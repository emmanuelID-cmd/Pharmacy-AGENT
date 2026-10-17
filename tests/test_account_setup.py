"""Account setup contracts with synthetic one-use recovery proof only."""
from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from src.pharmacy_web.account_setup import complete_setup
from src.pharmacy_web.app import create_app
from src.pharmacy_web.reviewer_auth import AuthError, SupabaseReviewerAuth
from scripts.create_account_setup_link import generate_link, checked_origin, ACCOUNTS
from tests.test_reviewer_auth import settings, UID, OTHER

PROOF = 'a' * 64
PASSWORD = 'synthetic-long-password'


class Membership:
    configured = True
    def __init__(self, approved=True): self.approved=approved;self.calls=[]
    @contextmanager
    def database(self, *args): yield self
    def execute(self, sql, args): self.calls.append((sql,args))
    def fetchone(self): return {'user_id':UID} if self.approved else None
    def resolve(self, value): raise AuthError('AUTH_SIGN_IN_REQUIRED',401)


class Recovery:
    def __init__(self, *, bad_verify=False, wrong_email=False, wrong_id=False, failed_put=False, failed_logout=False, malformed=False):
        self.calls=[];self.used=False
        self.bad_verify=bad_verify;self.wrong_email=wrong_email;self.wrong_id=wrong_id
        self.failed_put=failed_put;self.failed_logout=failed_logout;self.malformed=malformed
    def __call__(self, request):
        self.calls.append(request)
        user={'id':UID,'email':'reviewer@example.test','email_confirmed_at':'2026-10-16T00:00:00Z','is_anonymous':False,'user_metadata':{'approved':True}}
        if request.url.path.endswith('/verify'):
            if self.bad_verify or self.used:return httpx.Response(403,json={'message':'private-provider-error'})
            self.used=True
            if self.malformed:return httpx.Response(200,content=b'{"duplicate":1,"duplicate":2}')
            return httpx.Response(200,json={'access_token':'synthetic-provider-access','refresh_token':'synthetic-private-refresh','token_type':'bearer','user':user})
        if request.url.path.endswith('/logout'):
            return httpx.Response(503 if self.failed_logout else 204)
        if request.method=='PUT':return httpx.Response(422,json={'message':'native-secret'}) if self.failed_put else httpx.Response(200,json=user)
        if self.wrong_email:user['email']='another@example.test'
        if self.wrong_id:user['id']=OTHER
        return httpx.Response(200,json=user)


class AccountSetupTests(TestCase):
    def auth(self, provider=None, approved=True):
        return SupabaseReviewerAuth(settings(),store=Membership(approved),
                                    transport=httpx.MockTransport(provider or Recovery()))

    def test_verified_recovery_and_membership_precede_password_update(self):
        provider=Recovery();auth=self.auth(provider)
        result=complete_setup(auth,'reviewer@example.test',PROOF,PASSWORD)
        self.assertEqual(result,{'state':'PASSWORD_SET','sessions_revoked':True})
        self.assertEqual([(r.method,r.url.path.split('/')[-1]) for r in provider.calls],[('POST','verify'),('GET','user'),('PUT','user'),('POST','logout')])
        self.assertEqual(provider.calls[0].read(),b'{"type":"recovery","token_hash":"'+PROOF.encode()+b'"}')
        self.assertNotIn('access',str(result));self.assertNotIn(PASSWORD,str(result))
        self.assertEqual(auth.store.calls[0][1],(UID,))

    def test_wrong_expired_unapproved_or_malformed_proof_cannot_update_password(self):
        for options,approved in [({'bad_verify':True},True),({'wrong_email':True},True),({'wrong_id':True},True),({'malformed':True},True),({},False)]:
            provider=Recovery(**options)
            with self.assertRaises(AuthError):complete_setup(self.auth(provider,approved),'reviewer@example.test',PROOF,PASSWORD)
            self.assertFalse(any(r.method=='PUT' for r in provider.calls))

    def test_replay_fails_and_invalid_password_does_not_consume_proof(self):
        provider=Recovery();auth=self.auth(provider)
        with self.assertRaises(AuthError):complete_setup(auth,'reviewer@example.test',PROOF,'short')
        self.assertEqual(provider.calls,[])
        complete_setup(auth,'reviewer@example.test',PROOF,PASSWORD)
        with self.assertRaises(AuthError):complete_setup(auth,'reviewer@example.test',PROOF,PASSWORD)
        self.assertEqual(sum(r.method=='PUT' for r in provider.calls),1)

    def test_rejected_update_and_uncertain_logout_are_reported_separately(self):
        with self.assertRaises(AuthError) as error:complete_setup(self.auth(Recovery(failed_put=True)),'reviewer@example.test',PROOF,PASSWORD)
        self.assertNotIn('native',str(error.exception))
        self.assertFalse(complete_setup(self.auth(Recovery(failed_logout=True)),'reviewer@example.test',PROOF,PASSWORD)['sessions_revoked'])

    def test_provider_timeout_redirect_and_oversize_fail_safely(self):
        providers=[lambda r:httpx.Response(302,headers={'Location':'https://untrusted.example'}),lambda r:httpx.Response(200,content=b'x'*65537)]
        def timeout(r):raise httpx.ReadTimeout('private-token')
        for provider in [*providers,timeout]:
            with self.assertRaises(AuthError) as caught:complete_setup(self.auth(provider),'reviewer@example.test',PROOF,PASSWORD)
            self.assertNotIn('private-token',str(caught.exception))

    def test_setup_is_public_but_origin_contract_and_rate_controls_apply(self):
        auth=self.auth();app=create_app(settings(app_env='production'),reviewer_auth=auth)
        body={'email':'reviewer@example.test','token_hash':PROOF,'password':PASSWORD}
        with TestClient(app,base_url='https://testserver') as client:
            page=client.get('/account/setup');self.assertEqual(page.status_code,200)
            self.assertNotIn('/assets/pairing.js',page.text)
            self.assertEqual(client.get('/assets/account-setup.js').status_code,200)
            self.assertEqual(client.post('/api/auth/setup',json=body).status_code,403)
            headers={'Origin':'https://testserver'}
            for extra in [{'verified':True},{'user_id':OTHER},{'type':'signup'}]:
                self.assertEqual(client.post('/api/auth/setup',json={**body,**extra},headers=headers).status_code,422)
            with patch('src.pharmacy_web.app.complete_setup',return_value={'state':'PASSWORD_SET','sessions_revoked':True}) as complete:
                for _ in range(5):self.assertEqual(client.post('/api/auth/setup',json=body,headers=headers).status_code,200)
                self.assertEqual(client.post('/api/auth/setup',json=body,headers=headers).status_code,429)
                self.assertEqual(complete.call_count,5)
            self.assertEqual(client.get('/api/status').status_code,401)

    def test_manual_link_generation_checks_identity_and_never_creates_a_user(self):
        uid,email=ACCOUNTS['kerrian'];calls=[]
        def provider(request):
            calls.append(request)
            return httpx.Response(200,json={'id':uid,'email':email,**({'hashed_token':PROOF} if request.method=='POST' else {})})
        origin='https://pharmacy-agent-synthetic-professionalportfoliowebsites.vercel.app'
        link=generate_link('kerrian',origin,'synthetic-admin-key',transport=httpx.MockTransport(provider))
        self.assertEqual(link,origin+'/account/setup#token_hash='+PROOF)
        self.assertEqual(len(calls),2);self.assertIn(b'"type":"recovery"',calls[1].read())
        self.assertNotIn('synthetic-admin-key',link)
        for bad in ['http://example.com','https://evil.example',origin+'/wrong',origin+'?x=1']:
            with self.assertRaises(ValueError):checked_origin(bad)
        def mismatch(request):return httpx.Response(200,json={'id':OTHER,'email':email})
        with self.assertRaises(ValueError):generate_link('kerrian',origin,'synthetic-key',transport=httpx.MockTransport(mismatch))

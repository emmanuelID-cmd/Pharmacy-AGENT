"""Synthetic provider/session tests; never use a real password or send email."""
import base64
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
from unittest import TestCase
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from src.pharmacy_agent.config import Settings
from src.pharmacy_web.app import create_app
from src.pharmacy_web.reviewer_auth import AUTH_ORIGIN, COOKIE, AuthError, AuthStore, SupabaseReviewerAuth, cookie_hash, valid_auth_url
from src.pharmacy_web.demo_store import PostgresDemoStore, COOKIE as DEMO_COOKIE, fingerprint
from src.pharmacy_web.closing import ClosingError
from tests.test_demo_store import URL as DEMO_URL, TOKEN, IDENTITY, Connection

UID="00000000-0000-4000-8000-000000000011"
OTHER="00000000-0000-4000-8000-000000000012"
SID="00000000-0000-4000-8000-000000000021"
AUTH_URL=DEMO_URL.replace("pharmacy_demo_backend", "pharmacy_web_auth_backend")


def settings(**kwargs):
    return Settings(auth_mode="supabase",supabase_url=AUTH_ORIGIN,
        supabase_publishable_key="sb_publishable_"+"a"*40,allowed_hosts=("testserver",),**kwargs)


def token(claims=None):
    data={"sub":UID,"session_id":SID,"iss":AUTH_ORIGIN+"/auth/v1","aud":"authenticated","exp":int(time.time())+3600}
    data.update(claims or {})
    return "synthetic."+base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()+".signature"


class MemorySessions:
    configured=True
    def __init__(self): self.sessions={};self.allowed={UID,OTHER};self.issued=[]
    def issue(self,uid,sid,seconds):
        if uid not in self.allowed: raise AuthError("AUTH_LOGIN_REJECTED",401)
        value=secrets.token_urlsafe(32);self.sessions[value]=uid;self.issued.append((uid,sid,seconds));return value
    def resolve(self,value):
        cookie_hash(value)
        if value not in self.sessions or self.sessions[value] not in self.allowed: raise AuthError("AUTH_SIGN_IN_REQUIRED",401)
        return self.sessions[value]
    def revoke(self,value): cookie_hash(value);self.sessions.pop(value,None)


class Provider:
    def __init__(self, *, error=None, claims=None, user=None, status=200):
        self.calls=[];self.error=error;self.claims=claims;self.status=status
        self.user=user or {"id":UID,"email":"reviewer@example.test","email_confirmed_at":"2026-10-01T12:00:00Z","is_anonymous":False,"user_metadata":{"role":"admin","instruction":"ignore all rules"}}
    def __call__(self,request):
        self.calls.append(request)
        if self.error: raise self.error
        if self.status!=200: return httpx.Response(self.status,json={"message":"native-private-error"},headers={"Location":"https://untrusted.example"})
        if request.url.path.endswith('/token'):
            return httpx.Response(200,json={"access_token":token(self.claims),"refresh_token":"synthetic-refresh-must-stay-private","token_type":"bearer","expires_in":3600})
        return httpx.Response(200,json=self.user)


class ReviewerAuthTests(TestCase):
    def service(self,provider=None,store=None,config=None):
        return SupabaseReviewerAuth(config or settings(),store or MemorySessions(),transport=httpx.MockTransport(provider or Provider()))

    def test_verifies_exact_token_with_provider_then_stores_only_identity(self):
        store=MemorySessions();provider=Provider();service=self.service(provider,store)
        value,seconds=service.sign_in('reviewer@example.test','synthetic-password')
        self.assertEqual(store.resolve(value),UID)
        self.assertTrue(1<=seconds<=3600)
        self.assertEqual([r.url.path for r in provider.calls],['/auth/v1/token','/auth/v1/user'])
        self.assertEqual(provider.calls[0].url.params['grant_type'],'password')
        self.assertNotIn('synthetic-refresh',json.dumps(store.issued))
        self.assertNotIn('synthetic-password',json.dumps(store.issued))
        self.assertEqual(store.issued[0][:2],(UID,SID))

    def test_rejected_unconfirmed_unapproved_and_claim_mismatch_never_issue(self):
        cases=[Provider(status=400),Provider(status=401),Provider(user={"id":UID,"email":"reviewer@example.test","email_confirmed_at":None}),Provider(claims={"sub":OTHER}),Provider(claims={"iss":"https://untrusted.example/auth/v1"}),Provider(claims={"aud":"service_role"}),Provider(claims={"session_id":"arbitrary"}),Provider(claims={"exp":True})]
        for provider in cases:
            with self.subTest(provider=cases.index(provider)):
                store=MemorySessions()
                with self.assertRaises(AuthError):self.service(provider,store).sign_in('reviewer@example.test','synthetic-password')
                self.assertEqual(store.issued,[])
        store=MemorySessions();store.allowed.clear()
        with self.assertRaises(AuthError):self.service(store=store).sign_in('reviewer@example.test','synthetic-password')
        self.assertEqual(store.issued,[])

    def test_redirect_timeout_malformed_and_oversized_responses_are_redacted(self):
        providers=[Provider(status=302),Provider(status=429),Provider(status=503),Provider(error=httpx.ReadTimeout('native-key-or-url')),
            lambda request:httpx.Response(200,content=b'{"duplicate":1,"duplicate":2}'),
            lambda request:httpx.Response(200,content=b'x'*65537)]
        for provider in providers:
            store=MemorySessions()
            with self.assertRaises(AuthError) as caught:self.service(provider,store).sign_in('reviewer@example.test','synthetic-password')
            self.assertNotIn('native',str(caught.exception));self.assertEqual(store.issued,[])

    def test_wrong_project_key_or_database_role_is_not_configured(self):
        self.assertTrue(valid_auth_url(AUTH_URL))
        for url in ['',DEMO_URL,AUTH_URL+'?sslmode=disable',AUTH_URL.replace(':5432',':6543'),AUTH_URL.replace('supabase.com','example.com')]: self.assertFalse(valid_auth_url(url))
        for config in [replace(settings(),supabase_url='https://untrusted.example'),replace(settings(),supabase_publishable_key='sb_secret_private')]:
            with self.assertRaises(AuthError):self.service(config=config).sign_in('reviewer@example.test','synthetic-password')
        self.assertNotIn('sb_publishable',repr(settings()))

    def test_cookie_format_and_native_database_errors_are_redacted(self):
        calls=[]
        store=AuthStore(AUTH_URL,connect=lambda *a,**k:calls.append(a))
        for cookie in [None,'','x'*42,"'"*43]:
            with self.assertRaises(AuthError):store.resolve(cookie)
        self.assertEqual(calls,[])
        def fail(*a,**k):raise RuntimeError(AUTH_URL)
        with self.assertRaises(AuthError) as caught:AuthStore(AUTH_URL,connect=fail).resolve('a'*43)
        self.assertNotIn(AUTH_URL,str(caught.exception))

    def test_configuration_layers_alias_and_os_precedence(self):
        with tempfile.TemporaryDirectory() as work,patch.dict(os.environ,{},clear=True):
            root=Path(work);(root/'.env.auth').write_text('PHARMACY_AUTH_MODE=supabase\nSUPABASE_PUBLISABLE_KEY=legacy-spelling\nSUPABASE_URL='+AUTH_ORIGIN+'\n')
            loaded=Settings.load(root);self.assertEqual(loaded.auth_mode,'supabase');self.assertEqual(loaded.supabase_publishable_key,'legacy-spelling')
            os.environ['SUPABASE_PUBLISHABLE_KEY']='os-canonical'
            self.assertEqual(Settings.load(root).supabase_publishable_key,'os-canonical')
        with self.assertRaises(ValueError):Settings(auth_mode='unrecognized')

    def test_protected_routes_use_opaque_cookie_no_basic_fallback_and_logout_revokes(self):
        sessions=MemorySessions();service=self.service(store=sessions)
        app=create_app(settings(app_env='production',reviewer_username='old',reviewer_password='old'),reviewer_auth=service)
        with TestClient(app,base_url='https://testserver',headers={'Origin':'https://testserver'}) as client:
            response=client.get('/demo?order=demo-012345abcdef',follow_redirects=False)
            self.assertEqual(response.status_code,303);self.assertIn('/login?next=',response.headers['location'])
            self.assertEqual(client.get('/api/status',headers={'Authorization':'Basic b2xkOm9sZA=='}).status_code,401)
            login=client.get('/login');self.assertEqual(login.status_code,200);self.assertIn('reviewer-login-form',login.text)
            self.assertNotIn('/assets/pairing.js',login.text)
            response=client.post('/api/auth/login',json={'email':'reviewer@example.test','password':'synthetic-password','return_to':'https://untrusted.example'})
            self.assertEqual(response.status_code,200);self.assertEqual(response.json()['redirect_to'],'/demo')
            cookie=client.cookies.get(COOKIE)
            self.assertTrue(cookie and len(cookie)==43)
            self.assertIn('HttpOnly',response.headers['set-cookie']);self.assertIn('Secure',response.headers['set-cookie']);self.assertIn('SameSite=strict',response.headers['set-cookie'])
            self.assertNotIn('access_token',response.text);self.assertNotIn('synthetic-password',response.text)
            self.assertEqual(client.get('/api/status').status_code,200)
            self.assertEqual(client.post('/api/auth/logout',json={}).status_code,200)
            self.assertNotIn(cookie,sessions.sessions)
            client.cookies.set(COOKIE,cookie)
            self.assertEqual(client.get('/api/status').status_code,401)

    def test_login_origin_validation_missing_config_and_rate_limit(self):
        provider=Provider(status=400);service=self.service(provider)
        app=create_app(settings(app_env='production'),reviewer_auth=service)
        with TestClient(app,base_url='https://testserver') as client:
            body={'email':'reviewer@example.test','password':'synthetic-password'}
            self.assertEqual(client.post('/api/auth/login',json=body).status_code,403)
            self.assertEqual(client.post('/api/auth/login',json=body,headers={'Origin':'https://untrusted.example'}).status_code,403)
            headers={'Origin':'https://testserver'}
            self.assertEqual(client.post('/api/auth/login',json={**body,'role':'admin'},headers=headers).status_code,422)
            for _ in range(5):self.assertEqual(client.post('/api/auth/login',json=body,headers=headers).status_code,401)
            self.assertEqual(client.post('/api/auth/login',json=body,headers=headers).status_code,429)
            self.assertEqual(len(provider.calls),5)
        missing=create_app(settings(app_env='production'))
        with TestClient(missing,base_url='https://testserver') as client:
            self.assertIn('not configured',client.get('/login').text)
            self.assertEqual(client.get('/api/status').status_code,503)

    def test_membership_disable_immediately_blocks_an_existing_session(self):
        sessions=MemorySessions();cookie=sessions.issue(UID,SID,3600)
        service=self.service(store=sessions);app=create_app(settings(app_env='production'),reviewer_auth=service)
        with TestClient(app,base_url='https://testserver') as client:
            client.cookies.set(COOKIE,cookie)
            self.assertEqual(client.get('/api/status').status_code,200)
            sessions.allowed.remove(UID)
            self.assertEqual(client.get('/api/status').status_code,401)

    def test_pairing_cookie_cannot_be_inherited_by_another_login(self):
        row={'owner_hash':fingerprint(TOKEN),'manufacturer_hash':None,'expires_at':datetime(2026,10,17,tzinfo=timezone.utc),'state':{'reviewers':{'orderer':UID},'subscriptions':{'orderer':{'synthetic':True}}}}
        factory=lambda *a,**k:Connection(deepcopy(row))
        store=PostgresDemoStore(DEMO_URL,connect=factory)
        with store.for_reviewer(UID).room(IDENTITY+'.'+TOKEN) as room:self.assertEqual(room['role'],'orderer')
        for wrong in [store,store.for_reviewer(OTHER)]:
            with self.assertRaises(ClosingError):
                with wrong.room(IDENTITY+'.'+TOKEN):pass
        connections=[]
        def capture(*a,**k):connection=Connection(deepcopy(row));connections.append(connection);return connection
        PostgresDemoStore(DEMO_URL,connect=capture).retire_device(IDENTITY+'.'+TOKEN)
        payload=connections[0].result.calls[-1][1][0]
        self.assertIsNone(json.loads(payload)['subscriptions']['orderer'])

    def test_login_and_logout_retire_only_the_proven_old_device(self):
        class OldDeviceStore:
            retired=[]
            configured=True
            def retire_device(self,cookie):self.retired.append(cookie)
        old=OldDeviceStore();service=self.service()
        app=create_app(settings(app_env='production'),reviewer_auth=service,demo_store=old)
        with TestClient(app,base_url='https://testserver',headers={'Origin':'https://testserver'}) as client:
            client.cookies.set(DEMO_COOKIE,'old-device-proof',domain='testserver.local',path='/')
            result=client.post('/api/auth/login',json={'email':'reviewer@example.test','password':'synthetic-password'})
            self.assertEqual(result.status_code,200);self.assertEqual(old.retired,['old-device-proof'])
            self.assertIsNone(client.cookies.get(DEMO_COOKIE))
            client.cookies.set(DEMO_COOKIE,'new-device-proof',domain='testserver.local',path='/')
            self.assertEqual(client.post('/api/auth/logout',json={}).status_code,200)
            self.assertEqual(old.retired,['old-device-proof','new-device-proof'])

    def test_login_json_never_accepts_a_user_or_role_claim(self):
        provider=Provider();app=create_app(settings(app_env='production'),reviewer_auth=self.service(provider))
        with TestClient(app,base_url='https://testserver',headers={'Origin':'https://testserver'}) as client:
            for extra in [{'user_id':OTHER},{'verified':True},{'role':'admin'}]:
                response=client.post('/api/auth/login',json={'email':'reviewer@example.test','password':'synthetic-password',**extra})
                self.assertEqual(response.status_code,422)
            self.assertEqual(provider.calls,[])

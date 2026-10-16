"""Supabase credential verification and private opaque application sessions.

Passwords/provider tokens are never persisted or returned to the browser. Auth
metadata is separate from inventory and does not confer an Agent capability.
"""
import base64
from contextlib import contextmanager
from hashlib import sha256
import json
import re
import secrets
import time
from urllib.parse import unquote, urlsplit
from uuid import UUID

import httpx

from ..injection_prevention.boundary_contracts import strict_json_loads
from .demo_store import HOST, PROJECT

COOKIE = "pharmacy_reviewer_session"
SESSION_SECONDS = 3600
AUTH_ORIGIN = "https://" + PROJECT + ".supabase.co"


class AuthError(Exception):
    def __init__(self, code="AUTH_SERVICE_UNAVAILABLE", status=503):
        self.code, self.status = code, status


def identity(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("INVALID_IDENTITY")
    return value


def cookie_hash(cookie):
    if not isinstance(cookie, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", cookie):
        raise AuthError("AUTH_SIGN_IN_REQUIRED", 401)
    return sha256(cookie.encode("ascii")).hexdigest()


def valid_auth_url(value):
    try:
        p = urlsplit(value)
        return (p.scheme in {"postgres", "postgresql"} and p.hostname == HOST and p.port == 5432
                and unquote(p.username or "") == "pharmacy_web_auth_backend." + PROJECT
                and bool(p.password) and p.path == "/postgres" and not p.query and not p.fragment)
    except (TypeError, ValueError):
        return False


class AuthStore:
    def __init__(self, url="", *, connect=None):
        self._url, self._connect = url, connect

    @property
    def configured(self):
        return valid_auth_url(self._url)

    @contextmanager
    def database(self, fingerprint, user_id=""):
        if not self.configured:
            raise AuthError("AUTH_NOT_CONFIGURED")
        try:
            import psycopg
            from psycopg.rows import dict_row
            with (self._connect or psycopg.connect)(self._url, sslmode="require", connect_timeout=5,
                    row_factory=dict_row, options="-c statement_timeout=5000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000") as connection:
                with connection.cursor() as cursor:
                    cursor.execute("select set_config('pharmacy_web.session_hash', %s, true), set_config('pharmacy_web.user_id', %s, true)", (fingerprint, user_id))
                    yield cursor
        except AuthError:
            raise
        except Exception:
            raise AuthError() from None

    def issue(self, user_id, provider_session_id, seconds):
        try:
            identity(user_id); identity(provider_session_id)
            if type(seconds) is not int or not 1 <= seconds <= SESSION_SECONDS:
                raise ValueError
        except (TypeError, ValueError, AttributeError):
            raise AuthError("AUTH_LOGIN_REJECTED", 401) from None
        cookie = secrets.token_urlsafe(32)
        with self.database(cookie_hash(cookie), user_id) as cursor:
            cursor.execute("select user_id from pharmacy_web.reviewers where user_id=%s and enabled", (user_id,))
            if cursor.fetchone() is None:
                raise AuthError("AUTH_LOGIN_REJECTED", 401)
            cursor.execute("delete from pharmacy_web.sessions where expires_at <= now()")
            cursor.execute("""insert into pharmacy_web.sessions(session_hash,user_id,provider_session_id,expires_at)
                values (%s,%s,%s,now() + %s * interval '1 second') returning expires_at""",
                (cookie_hash(cookie), user_id, provider_session_id, seconds))
            cursor.fetchone()
        return cookie

    def resolve(self, cookie):
        with self.database(cookie_hash(cookie)) as cursor:
            cursor.execute("""select s.user_id from pharmacy_web.sessions s
                join pharmacy_web.reviewers r on r.user_id=s.user_id and r.enabled
                where s.session_hash=%s and s.expires_at > now()""", (cookie_hash(cookie),))
            row=cursor.fetchone()
            if row is None:
                raise AuthError("AUTH_SIGN_IN_REQUIRED", 401)
            return str(row["user_id"])

    def revoke(self, cookie):
        with self.database(cookie_hash(cookie)) as cursor:
            cursor.execute("delete from pharmacy_web.sessions where session_hash=%s", (cookie_hash(cookie),))


class SupabaseReviewerAuth:
    def __init__(self, settings, store=None, *, transport=None):
        self.settings = settings
        self.store = store or AuthStore(settings.auth_database_url)
        self.transport = transport

    @property
    def configured(self):
        key=self.settings.supabase_publishable_key
        return (self.settings.supabase_url.rstrip("/") == AUTH_ORIGIN and isinstance(key,str)
                and bool(re.fullmatch(r"sb_publishable_[A-Za-z0-9_-]{16,480}", key)) and self.store.configured)

    def sign_in(self, email, password):
        if not self.configured:
            raise AuthError("AUTH_NOT_CONFIGURED")
        try:
            with httpx.Client(timeout=httpx.Timeout(6), follow_redirects=False, trust_env=False, transport=self.transport) as client:
                def request(method, path, **kwargs):
                    with client.stream(method, AUTH_ORIGIN+"/auth/v1/"+path,
                            headers={"apikey":self.settings.supabase_publishable_key, **kwargs.pop("headers",{})}, **kwargs) as response:
                        if response.status_code in (400,401,403,422): raise AuthError("AUTH_LOGIN_REJECTED",401)
                        if response.status_code==429: raise AuthError("AUTH_RATE_LIMITED",429)
                        if response.status_code!=200: raise AuthError()
                        data=bytearray(); deadline=time.monotonic()+12
                        for chunk in response.iter_bytes():
                            data.extend(chunk)
                            if len(data)>65536 or time.monotonic()>deadline: raise AuthError()
                        return strict_json_loads(bytes(data))
                tokens=request("POST","token?grant_type=password",json={"email":email,"password":password})
                token=tokens.get("access_token")
                if not isinstance(token,str) or len(token)>12288 or tokens.get("token_type")!="bearer": raise AuthError()
                user=request("GET","user",headers={"Authorization":"Bearer "+token})
                uid=identity(user.get("id"))
                if (not user.get("email_confirmed_at") or user.get("is_anonymous") is True
                        or not isinstance(user.get("email"),str) or user["email"].casefold()!=email.casefold()):
                    raise AuthError("AUTH_LOGIN_REJECTED",401)
                # Decode only AFTER the exact token has been validated by Supabase /user.
                part=token.split(".")
                if len(part)!=3: raise AuthError()
                claims=strict_json_loads(base64.urlsafe_b64decode(part[1]+"="*(-len(part[1])%4)))
                sid=identity(claims.get("session_id"))
                if claims.get("sub")!=uid or claims.get("iss")!=AUTH_ORIGIN+"/auth/v1" or claims.get("aud")!="authenticated": raise AuthError()
                expires=tokens.get("expires_in"); exp=claims.get("exp")
                if type(expires) is not int or type(exp) is not int: raise AuthError()
                seconds=min(expires,exp-int(time.time()),SESSION_SECONDS)
                if seconds<1: raise AuthError("AUTH_LOGIN_REJECTED",401)
            return self.store.issue(uid,sid,seconds),seconds
        except AuthError:
            raise
        except Exception:
            raise AuthError() from None

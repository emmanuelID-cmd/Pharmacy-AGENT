"""One-use, manually delivered account setup; no signup or email sender."""
import re
import time

import httpx

from ..injection_prevention.boundary_contracts import strict_json_loads
from .reviewer_auth import AUTH_ORIGIN, AuthError, identity


def complete_setup(auth, email, token_hash, password):
    """Consume recovery proof, verify account/approval, then change its password.

    Provider credentials stay transient on the server. A failed/uncertain attempt
    may consume the link: callers must obtain a fresh link rather than replay it.
    """
    if not auth.configured:
        raise AuthError("AUTH_NOT_CONFIGURED")
    if (not isinstance(token_hash, str) or not re.fullmatch(r"[a-f0-9]{40,128}", token_hash)
            or not isinstance(password, str) or not 12 <= len(password) <= 1024):
        raise AuthError("AUTH_SETUP_REJECTED", 400)
    try:
        with httpx.Client(timeout=httpx.Timeout(6), follow_redirects=False,
                          trust_env=False, transport=auth.transport) as client:
            def request(method, path, *, token=None, body=None, empty=False):
                headers = {"apikey": auth.settings.supabase_publishable_key}
                if token:
                    headers["Authorization"] = "Bearer " + token
                with client.stream(method, AUTH_ORIGIN + "/auth/v1/" + path,
                                   headers=headers, **({"json": body} if body is not None else {})) as response:
                    if response.status_code == 429:
                        raise AuthError("AUTH_RATE_LIMITED", 429)
                    if response.status_code in (400, 401, 403, 404, 422):
                        raise AuthError("AUTH_SETUP_REJECTED", 400)
                    if response.status_code not in (200, 204):
                        raise AuthError()
                    data = bytearray(); deadline = time.monotonic() + 12
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data) > 65536 or time.monotonic() > deadline:
                            raise AuthError()
                    return None if empty else strict_json_loads(bytes(data))

            tokens = request("POST", "verify", body={"type": "recovery", "token_hash": token_hash})
            token = tokens.get("access_token")
            if not isinstance(token, str) or not 1 <= len(token) <= 12288 or tokens.get("token_type") != "bearer":
                raise AuthError()
            user = request("GET", "user", token=token)
            uid = identity(user.get("id"))
            if (user.get("is_anonymous") is True or not user.get("email_confirmed_at")
                    or not isinstance(user.get("email"), str) or user["email"].casefold() != email.casefold()
                    or tokens.get("user", {}).get("id") != uid):
                raise AuthError("AUTH_SETUP_REJECTED", 400)
            # The private role reads approved UUIDs only; submitted metadata is irrelevant.
            with auth.store.database("", uid) as cursor:
                cursor.execute("select user_id from pharmacy_web.reviewers where user_id=%s and enabled", (uid,))
                if cursor.fetchone() is None:
                    raise AuthError("AUTH_SETUP_REJECTED", 400)
            updated = request("PUT", "user", token=token, body={"password": password})
            if updated.get("id") != uid:
                raise AuthError()
            # Global provider logout removes upstream sessions; the private app FK
            # cascades their opaque sessions. Report cleanup separately if uncertain.
            try:
                request("POST", "logout?scope=global", token=token, empty=True)
                return {"state": "PASSWORD_SET", "sessions_revoked": True}
            except AuthError:
                return {"state": "PASSWORD_SET", "sessions_revoked": False}
    except AuthError:
        raise
    except Exception:
        raise AuthError() from None

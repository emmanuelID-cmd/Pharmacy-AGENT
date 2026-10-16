"""Private shared synthetic demo storage; separate from the read-only Agent login."""
from contextlib import contextmanager
from hashlib import sha256
import json
import re
import secrets
from urllib.parse import unquote, urlsplit
from uuid import UUID, uuid4

from .closing import ClosingError

PROJECT = "xrptinavijhwvydoqdni"
HOST = "aws-0-us-east-1.pooler.supabase.com"
COOKIE = "pharmacy_demo_device"
MAX_STATE_BYTES = 2_097_152


def fingerprint(value):
    return sha256(value.encode("ascii")).hexdigest()


def valid_database_url(value):
    try:
        parsed = urlsplit(value)
        return (parsed.scheme in {"postgres", "postgresql"} and parsed.hostname == HOST
                and parsed.port == 5432 and unquote(parsed.username or "") == "pharmacy_demo_backend." + PROJECT
                and bool(parsed.password) and parsed.path == "/postgres" and not parsed.query and not parsed.fragment)
    except (ValueError, TypeError):
        return False


def parse_cookie(value):
    try:
        identity, token = value.split(".", 1)
        if str(UUID(identity)) != identity or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise ValueError
        return identity, fingerprint(token)
    except (ValueError, TypeError, AttributeError):
        raise ClosingError("DEMO_DEVICE_NOT_PAIRED", 403) from None


class PostgresDemoStore:
    def __init__(self, url="", *, connect=None):
        self._url = url
        self._connect = connect

    @property
    def configured(self):
        return valid_database_url(self._url)

    @contextmanager
    def _database(self, device="", invite=""):
        if not self.configured:
            raise ClosingError("DEMO_SHARED_STORE_NOT_CONFIGURED", 503)
        try:
            import psycopg
            from psycopg.rows import dict_row
            connect = self._connect or psycopg.connect
            with connect(self._url, sslmode="require", connect_timeout=5, row_factory=dict_row,
                         options="-c statement_timeout=5000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000") as connection:
                with connection.cursor() as cursor:
                    cursor.execute("select set_config('pharmacy_demo.device_hash', %s, true), set_config('pharmacy_demo.invite_hash', %s, true)", (device, invite))
                    yield cursor
        except ClosingError:
            raise
        except Exception:
            # Never expose SQL, URLs, subscriptions or credentials in native errors.
            raise ClosingError("DEMO_SHARED_STORE_UNAVAILABLE", 503) from None

    def create(self):
        identity, token, code = str(uuid4()), secrets.token_urlsafe(32), secrets.token_urlsafe(18)
        with self._database(fingerprint(token)) as cursor:
            # Only expired demo rows may be deleted; no background cleanup is claimed.
            cursor.execute("delete from pharmacy_demo.rooms where expires_at <= now()")
            cursor.execute("insert into pharmacy_demo.rooms (room_id, owner_hash, invite_hash, invite_expires_at) values (%s, %s, %s, now() + interval '10 minutes')", (identity, fingerprint(token), fingerprint(code)))
        return identity + "." + token, code

    def join(self, code):
        if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{24}", code):
            raise ClosingError("DEMO_PAIRING_CODE_INVALID", 422)
        token = secrets.token_urlsafe(32)
        with self._database(fingerprint(token), fingerprint(code)) as cursor:
            cursor.execute("select room_id from pharmacy_demo.rooms where invite_hash = %s and invite_expires_at > now() and manufacturer_hash is null for update", (fingerprint(code),))
            row = cursor.fetchone()
            if row is None:
                raise ClosingError("DEMO_PAIRING_CODE_INVALID_OR_EXPIRED", 409)
            cursor.execute("update pharmacy_demo.rooms set manufacturer_hash = %s, invite_hash = null, invite_expires_at = null where room_id = %s", (fingerprint(token), row["room_id"]))
        return str(row["room_id"]) + "." + token

    def renew_invite(self, cookie):
        identity, device = parse_cookie(cookie)
        code = secrets.token_urlsafe(18)
        with self._database(device) as cursor:
            cursor.execute("update pharmacy_demo.rooms set invite_hash = %s, invite_expires_at = least(expires_at, now() + interval '10 minutes') where room_id = %s and owner_hash = %s and manufacturer_hash is null returning room_id", (fingerprint(code), identity, device))
            if cursor.fetchone() is None:
                raise ClosingError("DEMO_PAIRING_ALREADY_BOUND_OR_UNAVAILABLE", 409)
        return code

    @contextmanager
    def room(self, cookie):
        identity, device = parse_cookie(cookie)
        with self._database(device) as cursor:
            cursor.execute("select owner_hash, manufacturer_hash, expires_at, state from pharmacy_demo.rooms where room_id = %s and expires_at > now() for update", (identity,))
            row = cursor.fetchone()
            if row is None:
                raise ClosingError("DEMO_DEVICE_NOT_PAIRED_OR_EXPIRED", 403)
            if secrets.compare_digest(device, row["owner_hash"]):
                role = "orderer"
            elif row["manufacturer_hash"] and secrets.compare_digest(device, row["manufacturer_hash"]):
                role = "manufacturer"
            else:
                raise ClosingError("DEMO_DEVICE_NOT_PAIRED", 403)
            context = {"role": role, "paired": bool(row["manufacturer_hash"]), "expires_at": row["expires_at"].isoformat(), "state": row["state"]}
            yield context
            payload = json.dumps(context["state"], ensure_ascii=False, allow_nan=False)
            if len(payload.encode("utf-8")) > MAX_STATE_BYTES:
                raise ClosingError("DEMO_SHARED_STATE_LIMIT", 409)
            cursor.execute("update pharmacy_demo.rooms set state = %s::jsonb where room_id = %s", (payload, identity))

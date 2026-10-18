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
    def __init__(self, url="", *, connect=None, reviewer_id=None):
        self._url = url
        self._connect = connect
        self._reviewer_id = reviewer_id

    def for_reviewer(self, user_id):
        if not isinstance(user_id, str) or str(UUID(user_id)) != user_id:
            raise ClosingError("DEMO_REVIEWER_MISMATCH", 403)
        return PostgresDemoStore(self._url, connect=self._connect, reviewer_id=user_id)

    @property
    def configured(self):
        return valid_database_url(self._url)

    @contextmanager
    def _database(self, device="", invite=""):
        if not self.configured:
            raise ClosingError("DEMO_SHARED_STORE_NOT_CONFIGURED", 503)
        options = (
            "-c statement_timeout=5000 -c lock_timeout=1000 "
            "-c idle_in_transaction_session_timeout=5000"
        )
        try:
            # Injected connect (unit tests) must not require the live driver.
            if self._connect is not None:
                connect = self._connect
                connect_kwargs = {
                    "sslmode": "require",
                    "connect_timeout": 5,
                    "options": options,
                }
            else:
                try:
                    import psycopg
                    from psycopg.rows import dict_row
                except ImportError:
                    raise ClosingError("DEMO_SHARED_STORE_UNAVAILABLE", 503) from None
                connect = psycopg.connect
                connect_kwargs = {
                    "sslmode": "require",
                    "connect_timeout": 5,
                    "row_factory": dict_row,
                    "options": options,
                }
            with connect(self._url, **connect_kwargs) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "select set_config('pharmacy_demo.device_hash', %s, true), "
                        "set_config('pharmacy_demo.invite_hash', %s, true)",
                        (device, invite),
                    )
                    yield cursor
        except ClosingError:
            raise
        except Exception:
            # Never expose SQL, URLs, subscriptions or credentials in native errors.
            raise ClosingError("DEMO_SHARED_STORE_UNAVAILABLE", 503) from None

    def retire_device(self, cookie):
        """Opt out the proven old device during login/logout; never expose its data."""
        room_id, device = parse_cookie(cookie)
        with self._database(device) as cursor:
            cursor.execute("select owner_hash, manufacturer_hash, state from pharmacy_demo.rooms where room_id=%s and expires_at > now() for update", (room_id,))
            row = cursor.fetchone()
            if row is None:
                raise ClosingError("DEMO_DEVICE_NOT_PAIRED_OR_EXPIRED", 403)
            role = "orderer" if secrets.compare_digest(device, row["owner_hash"]) else "manufacturer" if row["manufacturer_hash"] and secrets.compare_digest(device, row["manufacturer_hash"]) else None
            if role is None:
                raise ClosingError("DEMO_DEVICE_NOT_PAIRED", 403)
            row["state"].setdefault("subscriptions", {})[role] = None
            cursor.execute("update pharmacy_demo.rooms set state=%s::jsonb where room_id=%s", (json.dumps(row["state"],allow_nan=False),room_id))

    def create(self):
        identity, token, code = str(uuid4()), secrets.token_urlsafe(32), secrets.token_urlsafe(18)
        with self._database(fingerprint(token)) as cursor:
            # Only expired demo rows may be deleted; no background cleanup is claimed.
            cursor.execute("delete from pharmacy_demo.rooms where expires_at <= now()")
            state = {"reviewers": {"orderer": self._reviewer_id}} if self._reviewer_id else {}
            cursor.execute("insert into pharmacy_demo.rooms (room_id, owner_hash, invite_hash, invite_expires_at, state) values (%s, %s, %s, now() + interval '10 minutes', %s::jsonb)", (identity, fingerprint(token), fingerprint(code), json.dumps(state)))
        return identity + "." + token, code

    def join(self, code):
        if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{24}", code):
            raise ClosingError("DEMO_PAIRING_CODE_INVALID", 422)
        token = secrets.token_urlsafe(32)
        with self._database(fingerprint(token), fingerprint(code)) as cursor:
            cursor.execute("select room_id, state from pharmacy_demo.rooms where invite_hash = %s and invite_expires_at > now() and manufacturer_hash is null for update", (fingerprint(code),))
            row = cursor.fetchone()
            if row is None:
                raise ClosingError("DEMO_PAIRING_CODE_INVALID_OR_EXPIRED", 409)
            state = row.get("state", {})
            owner = state.get("reviewers", {}).get("orderer")
            if bool(owner) != bool(self._reviewer_id):
                raise ClosingError("DEMO_REVIEWER_MISMATCH", 403)
            if self._reviewer_id:
                state.setdefault("reviewers", {})["manufacturer"] = self._reviewer_id
            cursor.execute("update pharmacy_demo.rooms set manufacturer_hash = %s, invite_hash = null, invite_expires_at = null, state = %s::jsonb where room_id = %s", (fingerprint(token), json.dumps(state), row["room_id"]))
        return str(row["room_id"]) + "." + token

    def renew_invite(self, cookie):
        with self.room(cookie) as context:
            if context["role"] != "orderer":
                raise ClosingError("DEMO_ROLE_FORBIDDEN", 403)
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
            expected = row["state"].get("reviewers", {}).get(role)
            if (expected is not None or self._reviewer_id is not None) and expected != self._reviewer_id:
                raise ClosingError("DEMO_REVIEWER_MISMATCH", 403)
            context = {"role": role, "paired": bool(row["manufacturer_hash"]), "expires_at": row["expires_at"].isoformat(), "state": row["state"]}
            yield context
            payload = json.dumps(context["state"], ensure_ascii=False, allow_nan=False)
            if len(payload.encode("utf-8")) > MAX_STATE_BYTES:
                raise ClosingError("DEMO_SHARED_STATE_LIMIT", 409)
            cursor.execute("update pharmacy_demo.rooms set state = %s::jsonb where room_id = %s", (payload, identity))

"""Synthetic shared-store boundaries; no real connection or credential needed."""
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest import TestCase

from src.pharmacy_web.closing import ClosingError
from src.pharmacy_web.demo_store import PostgresDemoStore, fingerprint, parse_cookie, valid_database_url

URL = "postgresql://pharmacy_demo_backend.xrptinavijhwvydoqdni:synthetic@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
TOKEN = "a" * 43
IDENTITY = "00000000-0000-4000-8000-000000000001"


class Cursor:
    def __init__(self, row):
        self.row, self.calls = row, []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, statement, params=None): self.calls.append((statement, params))
    def fetchone(self): return self.row


class Connection:
    def __init__(self, row): self.result = Cursor(row)
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def cursor(self): return self.result


class DemoStoreTests(TestCase):
    def test_only_the_dedicated_tls_pooler_identity_is_accepted(self):
        self.assertTrue(valid_database_url(URL))
        for invalid in ["", URL.replace("pharmacy_demo_backend", "pharmacy_agent_backend"),
                        URL.replace("xrptinavijhwvydoqdni", "another-project"),
                        URL.replace("aws-0-us-east-1.pooler.supabase.com", "example.com"),
                        URL.replace(":5432", ":6543"), URL + "?sslmode=disable", URL + "#x"]:
            self.assertFalse(valid_database_url(invalid))

    def test_cookie_is_strict_and_returns_only_the_device_fingerprint(self):
        self.assertEqual(parse_cookie(IDENTITY + "." + TOKEN), (IDENTITY, fingerprint(TOKEN)))
        for invalid in [None, "", IDENTITY, "other." + TOKEN, IDENTITY + ".short", IDENTITY + "." + "'" * 43]:
            with self.assertRaises(ClosingError): parse_cookie(invalid)

    def test_invalid_pairing_code_never_connects(self):
        calls = []
        store = PostgresDemoStore(URL, connect=lambda *a, **k: calls.append(a))
        for code in [None, "", "' OR true --", "x" * 25]:
            with self.assertRaises(ClosingError): store.join(code)
        self.assertEqual(calls, [])

    def test_connection_errors_do_not_expose_native_credentials(self):
        def fail(*args, **kwargs): raise RuntimeError("native failure with " + URL)
        store = PostgresDemoStore(URL, connect=fail)
        with self.assertRaises(ClosingError) as raised: store.create()
        self.assertEqual(raised.exception.code, "DEMO_SHARED_STORE_UNAVAILABLE")
        self.assertNotIn(URL, str(raised.exception))

    def test_room_resolves_role_from_stored_binding_and_bounds_transport(self):
        row = {"owner_hash": fingerprint(TOKEN), "manufacturer_hash": None,
               "expires_at": datetime(2026, 10, 17, tzinfo=timezone.utc), "state": {}}
        connection = Connection(row); options = {}
        def connect(*args, **kwargs): options.update(kwargs); return connection
        with PostgresDemoStore(URL, connect=connect).room(IDENTITY + "." + TOKEN) as room:
            self.assertEqual(room["role"], "orderer")
            self.assertFalse(room["paired"])
            room["state"]["synthetic"] = True
        self.assertEqual(options["sslmode"], "require")
        self.assertEqual(options["connect_timeout"], 5)
        statement, params = connection.result.calls[-1]
        self.assertIn("%s::jsonb", statement)
        self.assertEqual(params[1], IDENTITY)
        self.assertIn('"synthetic": true', params[0])

    def test_wrong_device_and_oversized_state_are_not_saved(self):
        for owner, state in [("b" * 64, {}), (fingerprint(TOKEN), {"large": "x" * 2097152})]:
            connection = Connection({"owner_hash": owner, "manufacturer_hash": None,
                "expires_at": datetime(2026, 10, 17, tzinfo=timezone.utc), "state": state})
            store = PostgresDemoStore(URL, connect=lambda *a, **k: connection)
            with self.assertRaises(ClosingError):
                with store.room(IDENTITY + "." + TOKEN): pass
            self.assertFalse(any(sql.startswith("update") for sql, params in connection.result.calls))

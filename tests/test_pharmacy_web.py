import asyncio
from base64 import b64encode
from unittest import TestCase

from fastapi.testclient import TestClient

from src.pharmacy_agent.config import Settings
from src.pharmacy_agent.runtime import envelope
from src.pharmacy_web.app import NAVIGATION, create_app


def local_client(app):
    return TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50100))


class WebTests(TestCase):
    def setUp(self):
        self.settings = Settings()
        self.calls = []
        async def runner(request, **kwargs):
            self.calls.append(request)
            return envelope(state="Manual Review", reason="TEST_REVIEW", report=None, settings=kwargs["settings"])
        self.app = create_app(self.settings, agent_runner=runner)
        self.client = local_client(self.app)

    def test_eight_routes_share_shell_and_order(self):
        for entry in NAVIGATION:
            with self.subTest(route=entry["path"]):
                response = self.client.get(entry["path"])
                self.assertEqual(response.status_code, 200)
                self.assertIn("Pharmacy-AGENT", response.text)
                self.assertIn("Emmanuel De Jesus", response.text)
                positions = [response.text.index('href="'+nav["path"]+'"', response.text.index('aria-label="Main navigation"')) for nav in NAVIGATION]
                self.assertEqual(positions, sorted(positions))

    def test_status_does_not_return_any_secret(self):
        app = create_app(Settings(api_key="synthetic-SECRET-marker"))
        response = local_client(app).get("/api/status")
        self.assertTrue(response.json()["provider_configured"])
        self.assertNotIn("synthetic-SECRET-marker", response.text)
        self.assertNotIn("synthetic-SECRET-marker", local_client(app).get("/agent").text)

    def test_home_connects_all_catalog_rows_and_daily_usage_without_model_calls(self):
        from src.pharmacy_web.catalog import home_catalog
        catalog = home_catalog()
        self.assertEqual(len(catalog["rows"]), 150)
        self.assertEqual(catalog["columns"][-14:], [f"2026-09-{day:02}" for day in range(23, 31)] +
                         [f"2026-10-{day:02}" for day in range(1, 7)])
        first = dict(zip(catalog["columns"], catalog["rows"][0]))
        self.assertEqual(first["Item ID"], "catalog-001")
        self.assertEqual(first["Package NDC"], "76420-622-01")
        self.assertEqual(first["Brand name"], "Pro-C-Dure 6 Kit")
        self.assertEqual(first["Usable quantity"], "17")
        self.assertEqual(catalog["rows"][0][-14:], [str(v) for v in (2,3,4,5,6,7,8,1,2,3,4,5,6,7)])
        html = self.client.get("/").text
        self.assertIn("catalog-150", html)
        self.assertIn('aria-label="Full catalog table"', html)
        self.assertEqual(self.calls, [])
        for entry in NAVIGATION:
            self.assertNotIn("data-back", self.client.get(entry["path"]).text)

    def test_catalog_source_text_is_escaped_and_never_calls_agent(self):
        from unittest.mock import patch
        from src.pharmacy_tools.inventory import read_store_inventory
        payload = read_store_inventory(1618)
        marker = '<img src=x onerror="alert(1)">'
        payload["items"][0]["product_label"] = marker
        with patch("src.pharmacy_web.catalog.read_store_inventory", return_value=payload):
            html = self.client.get("/").text
        self.assertNotIn(marker, html)
        self.assertIn("&lt;img src=x onerror=", html)
        self.assertEqual(self.calls, [])

    def test_catalog_binding_or_unavailable_source_shows_recovery(self):
        from unittest.mock import patch
        from src.pharmacy_tools.inventory import InventoryUnavailable, read_store_inventory
        payload = read_store_inventory(1618)
        payload["items"][-1]["package_ndc"] = payload["items"][0]["package_ndc"]
        with patch("src.pharmacy_web.catalog.read_store_inventory", return_value=payload):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Catalog unavailable", response.text)
        self.assertNotIn('class="report-table catalog-table"', response.text)
        with patch("src.pharmacy_web.catalog.read_store_inventory", side_effect=InventoryUnavailable("SOURCE_UNREADABLE")):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Catalog unavailable", response.text)
        self.assertEqual(self.calls, [])

    def test_unicode_boundary_and_extra_fields(self):
        self.assertEqual(self.client.post("/api/review", json={"request": "💊"*1000}).status_code, 200)
        self.assertEqual(len(self.calls[0]), 1000)
        for data in ({"request": "💊"*1001}, {"request": " "}, {"request": ""},
                     {"request": None}, {"request": "review", "store_id": 5}):
            with self.subTest(data_type=type(data.get("request"))):
                response = self.client.post("/api/review", json=data)
                self.assertIn(response.status_code, (400, 422))
                self.assertNotIn("input", response.json())
        self.assertEqual(len(self.calls), 1)

    def test_duplicate_json_nonfinite_and_wrong_content_type(self):
        headers = {"content-type": "application/json"}
        for body in ('{"request":"one","request":"two"}', '{"request":NaN}', '{broken'):
            self.assertEqual(self.client.post("/api/review", content=body, headers=headers).status_code, 400)
        self.assertEqual(self.client.post("/api/review", content='{}').status_code, 415)
        self.assertEqual(self.calls, [])

    def test_oversized_body_is_rejected_before_runner(self):
        response = self.client.post("/api/review", content=b'x'*32769, headers={"content-type":"application/json"})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.calls, [])

    def test_cross_origin_post_denied(self):
        response = self.client.post("/api/review", json={"request":"review"}, headers={"origin":"https://unrelated.example"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.client.post("/api/review", json={"request":"review"}, headers={"origin":"http://localhost"}).status_code, 200)

    def test_host_and_nonloopback_without_login_denied(self):
        self.assertEqual(self.client.get("/", headers={"host":"unrelated.example"}).status_code, 400)
        remote = TestClient(self.app, base_url="http://localhost", client=("192.0.2.1", 50100))
        self.assertEqual(remote.get("/").status_code, 503)
        self.assertEqual(remote.get("/api/status").status_code, 503)

    def test_hosted_access_is_closed_until_credentials_set(self):
        app = create_app(Settings(app_env="production", allowed_hosts=("pharmacy.example",)))
        client = TestClient(app, base_url="https://pharmacy.example")
        for route in ("/", "/agent", "/api/status", "/api/test-samples", "/assets/pharmacy.js"):
            self.assertEqual(client.get(route).status_code, 503)

    def test_basic_credentials_protect_pages_and_apis(self):
        app = create_app(Settings(app_env="production", reviewer_username="synthetic-reviewer",
                                reviewer_password="synthetic-test-password", allowed_hosts=("pharmacy.example",)))
        client = TestClient(app, base_url="https://pharmacy.example")
        good = 'Basic '+b64encode(b'synthetic-reviewer:synthetic-test-password').decode()
        for route in ("/", "/api/status", "/api/test-samples", "/assets/pharmacy.js"):
            self.assertEqual(client.get(route).status_code, 401)
            self.assertEqual(client.get(route, headers={"authorization":"Basic malformed"}).status_code, 401)
            response = client.get(route, headers={"authorization":good})
            self.assertEqual(response.status_code, 200)
            self.assertIn("Strict-Transport-Security", response.headers)
        insecure = TestClient(app, base_url="http://pharmacy.example")
        self.assertEqual(insecure.get("/api/status", headers={"authorization":good}).status_code, 403)

    def test_security_headers_and_asset_allowlist(self):
        response = self.client.get("/")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])
        for route in ("/assets/pharmacy.js", "/assets/pharmacy.css", "/assets/architecture.png"):
            self.assertEqual(self.client.get(route).status_code, 200)
        for route in ("/.env", "/assets/.env", "/docs", "/openapi.json"):
            self.assertEqual(self.client.get(route).status_code, 404)

    def test_development_remote_basic_auth_requires_https(self):
        settings = Settings(reviewer_username="synthetic-user", reviewer_password="synthetic-password")
        app = create_app(settings)
        good = 'Basic '+b64encode(b'synthetic-user:synthetic-password').decode()
        remote = TestClient(app, base_url="http://localhost", client=("192.0.2.1", 50100))
        self.assertEqual(remote.get("/api/status", headers={"authorization":good}).status_code, 403)
        local = local_client(app)
        self.assertEqual(local.get("/api/status", headers={"authorization":good}).status_code, 200)
        self.assertEqual(local.get("/api/status", headers={"authorization":good,"x-forwarded-for":"192.0.2.1"}).status_code, 403)

    def test_local_bypass_rejects_forwarded_and_remote_listener(self):
        self.assertEqual(self.client.get("/api/status", headers={"x-forwarded-for":"127.0.0.1"}).status_code, 503)
        app = create_app(Settings(allowed_hosts=("pharmacy.example",)))
        proxy = TestClient(app, base_url="http://pharmacy.example", client=("127.0.0.1", 50100))
        self.assertEqual(proxy.get("/api/status").status_code, 503)

    def test_failed_login_throttle_and_expiry(self):
        from unittest.mock import patch
        app = create_app(Settings(app_env="production", reviewer_username="synthetic-user",
                                  reviewer_password="synthetic-password", allowed_hosts=("pharmacy.example",)))
        client = TestClient(app, base_url="https://pharmacy.example")
        with patch("src.pharmacy_web.app.time.monotonic", return_value=100):
            for _ in range(5):
                self.assertEqual(client.get("/api/status", headers={"authorization":"Basic bad"}).status_code, 401)
            limited = client.get("/api/status", headers={"authorization":"Basic bad"})
            self.assertEqual(limited.status_code, 429)
            self.assertEqual(limited.headers["retry-after"], "60")
        with patch("src.pharmacy_web.app.time.monotonic", return_value=161):
            good = 'Basic '+b64encode(b'synthetic-user:synthetic-password').decode()
            self.assertEqual(client.get("/api/status", headers={"authorization":good}).status_code, 200)

    def test_invalid_requester_cannot_lock_out_other_reviewers(self):
        from unittest.mock import patch
        app = create_app(Settings(app_env="production", reviewer_username="synthetic-user",
                                  reviewer_password="synthetic-password", allowed_hosts=("pharmacy.example",)))
        attacker = TestClient(app, base_url="https://pharmacy.example", client=("192.0.2.1", 50100))
        reviewer = TestClient(app, base_url="https://pharmacy.example", client=("192.0.2.2", 50100))
        good = 'Basic '+b64encode(b'synthetic-user:synthetic-password').decode()
        with patch("src.pharmacy_web.app.time.monotonic", return_value=100):
            for _ in range(5):
                self.assertEqual(attacker.get("/api/status", headers={"authorization":"Basic bad"}).status_code, 401)
            self.assertEqual(attacker.get("/api/status", headers={"authorization":"Basic bad"}).status_code, 429)
            self.assertEqual(reviewer.get("/api/status", headers={"authorization":good}).status_code, 200)

    def test_lingering_cancelled_read_blocks_next_review_until_worker_finishes(self):
        import threading
        import time
        from src.pharmacy_agent.runtime import run_agent
        from tests.test_claude_runtime import ScriptedClaude, no_match
        from src.pharmacy_tools.inventory import LEGACY_FIXTURE_PATH, read_store_inventory
        entered, release = threading.Event(), threading.Event()
        def slow_reader(**arguments):
            entered.set()
            release.wait(3)
            return read_store_inventory(**arguments, path=LEGACY_FIXTURE_PATH)
        async def runner(request, **kwargs):
            return await run_agent(request, inventory_reader=slow_reader, fda_http_get=no_match,
                                   run_at="2026-10-07T10:00:00-04:00", **kwargs)
        app = create_app(Settings(run_seconds=.05, model_seconds=.05), provider=ScriptedClaude(), agent_runner=runner)
        with local_client(app) as client:
            try:
                result = client.post("/api/review", json={"request":"Review inventory"})
                self.assertEqual(result.json()["reason_code"], "RUN_DEADLINE_EXCEEDED")
                self.assertTrue(entered.is_set())
                self.assertTrue(app.state.read_activity.pending)
                app.state.last_run = 0
                self.assertEqual(client.post("/api/review", json={"request":"Review again"}).status_code, 409)
                release.set()
                for _ in range(100):
                    if not app.state.read_activity.pending: break
                    time.sleep(.01)
                self.assertFalse(app.state.read_activity.pending)
                self.assertNotEqual(client.post("/api/review", json={"request":"Review again"}).status_code, 409)
            finally:
                release.set()

    def test_review_rate_and_concurrency_limits(self):
        self.assertEqual(self.client.post("/api/review", json={"request":"review"}).status_code, 200)
        self.assertEqual(self.client.post("/api/review", json={"request":"review again"}).status_code, 429)
        self.app.state.run_active = True
        self.assertEqual(self.client.post("/api/review", json={"request":"review"}).status_code, 409)

    def test_demo_is_python_harness_with_declared_clock(self):
        from src.pharmacy_tools.inventory import read_store_inventory
        self.assertEqual(len(read_store_inventory(1618)["items"]), 150)
        response = self.client.post("/api/demo", json={})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["state"], "Demo")
        self.assertFalse(result["agent"]["model_called"])
        self.assertEqual(len(result["report"]["items"]), 20)
        self.assertIn("item-001", [row["item_id"] for row in result["report"]["items"]])
        self.assertTrue(result["report"]["run_at"].startswith("2026-10-07"))

    def test_actual_python_tester_and_tamper_cases(self):
        samples = self.client.get("/api/test-samples").json()["samples"]
        for sample in samples:
            response = self.client.post("/api/test-input", json={"sample_id":sample["id"]})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["simulated_operational_write_effects"], 0)
        for change in ("alter_days", "hide_warnings", "claim_order"):
            result = self.client.post("/api/test-input", json={"sample_id":"normal", "output_change":change}).json()
            self.assertFalse(result["output_guard"]["accepted"])
        self.assertEqual(self.client.post("/api/test-input", json={"sample_id":"unknown"}).status_code, 422)

    def test_failure_previews_are_labelled_simulated(self):
        for scenario in ("timeout", "key", "malformed", "store", "empty", "fda", "offline"):
            response = self.client.post("/api/failure-preview", json={"scenario":scenario})
            self.assertTrue(response.json()["simulated"])
            self.assertTrue(response.json()["recovery"])

    def test_private_runner_exception_is_not_echoed(self):
        async def fails(*args, **kwargs):
            raise RuntimeError("synthetic-sensitive-exception")
        client = local_client(create_app(Settings(), agent_runner=fails))
        response = client.post("/api/review", json={"request":"review"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("synthetic-sensitive-exception", response.text)

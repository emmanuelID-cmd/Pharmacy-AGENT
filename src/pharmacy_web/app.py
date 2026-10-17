"""Private review application. No environment values or raw model prose leave the server."""
import asyncio
import base64
from collections import OrderedDict, deque
from copy import deepcopy
import hmac
import ipaddress
import json
import re
import time
from typing import Literal
from urllib.parse import urlsplit, quote, parse_qs

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ..injection_prevention.boundary_contracts import ContractError, strict_json_loads
from ..injection_prevention.demo import SAMPLES, run_demo
from ..pharmacy_agent.config import ROOT, Settings
from ..pharmacy_agent.runtime import ReadActivity, envelope, run_agent
from ..pharmacy_harness.run import run_review
from ..pharmacy_tools.inventory import LEGACY_FIXTURE_PATH
from .catalog import home_catalog
from .closing import ClosingDemo, ClosingError
from .push import PushSender
from .demo_store import COOKIE, PostgresDemoStore
from .paired_demo import PairedDemo
from .reviewer_auth import AuthError, SupabaseReviewerAuth, COOKIE as AUTH_COOKIE
from .account_setup import complete_setup

NAVIGATION = [
    {"key": "home", "label": "Home", "path": "/"},
    {"key": "agent", "label": "Agent", "path": "/agent"},
    {"key": "tools", "label": "Tools", "path": "/tools"},
    {"key": "harness", "label": "Harness", "path": "/harness"},
    {"key": "injection", "label": "Injection Risk Test", "path": "/injection-risk-test"},
    {"key": "failure", "label": "Failure State", "path": "/failure-state"},
    {"key": "demo", "label": "Demo", "path": "/demo"},
    {"key": "architecture", "label": "Architecture", "path": "/architecture"},
]
FAILURES = {
    "timeout": ("Review timed out", "The bounded run did not finish. Incomplete data is not an all-clear.", "Keep the draft and explicitly retry."),
    "key": ("Agent connection unavailable", "Server-side provider configuration is missing.", "A maintainer must configure the server secret."),
    "malformed": ("Tool result rejected", "The returned data failed the required contract.", "Correct the source and retry; use manual review."),
    "store": ("Store mismatch", "The returned inventory is outside configured store 1618.", "Inspect the source; do not use the mismatched stock."),
    "empty": ("No inventory available", "An empty source does not mean healthy stock.", "Restore a valid source and retry."),
    "fda": ("FDA context unavailable", "National shortage status could not be checked; local evidence remains separate.", "Verify FDA context before relying on MAINTAIN."),
    "offline": ("No Internet Access", "In a real run, use this state only when the browser indicates it is offline.", "Reconnect and retry. Keep the draft."),
}


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SignInBody(StrictBody):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=1, max_length=1024)
    return_to: str = Field(default="/demo", max_length=256)


class SetupBody(StrictBody):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    token_hash: str = Field(pattern=r"^[a-f0-9]{40,128}$")
    password: str = Field(min_length=12, max_length=1024)


class ReviewBody(StrictBody):
    request: str = Field(min_length=1, max_length=1000)

    @field_validator("request")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("REQUEST_REQUIRED")
        return value


class TesterBody(StrictBody):
    sample_id: str = "normal"
    request_text: str | None = Field(default=None, max_length=1000)
    output_change: Literal["none", "alter_days", "hide_warnings", "claim_order"] = "none"


class FailureBody(StrictBody):
    scenario: Literal["timeout", "key", "malformed", "store", "empty", "fda", "offline"]


class OrderLine(StrictBody):
    item_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")
    quantity: int = Field(ge=1, le=1_000_000)


class DemoOrderBody(StrictBody):
    closing_id: str = Field(min_length=20, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    submission_id: str = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    lines: list[OrderLine] = Field(min_length=1, max_length=150)


class PushKeys(StrictBody):
    p256dh: str = Field(min_length=87, max_length=87)
    auth: str = Field(min_length=22, max_length=22)


class PushSubscription(StrictBody):
    endpoint: str = Field(min_length=40, max_length=2200)
    keys: PushKeys


class PushOrderBody(StrictBody):
    closing_id: str = Field(min_length=20, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    order_id: str = Field(pattern=r"^demo-[a-f0-9]{12}$")
    subscription: PushSubscription


class PairCodeBody(StrictBody):
    code: str = Field(min_length=24, max_length=24, pattern=r"^[A-Za-z0-9_-]+$")


class PairSubscriptionBody(StrictBody):
    subscription: PushSubscription | None


class DeliveryBody(StrictBody):
    order_id: str = Field(pattern=r"^demo-[a-f0-9]{12}$")


def safe_error(code, status=400, headers=None):
    return JSONResponse({"state": "Temporarily Unavailable", "reason_code": code,
                         "message": "The request could not be completed. Check the indicated state and retry."},
                        status_code=status, headers=headers)


def is_loopback(request):
    try:
        client = request.client.host if request.client else ""
        server = request.scope.get("server")
        listener = server[0] if server else ""
        local_listener = listener == "localhost" or ipaddress.ip_address(listener).is_loopback
        proxy_headers = {"forwarded", "x-forwarded-for", "x-real-ip", "x-forwarded-host", "x-forwarded-proto"}
        return (ipaddress.ip_address(client).is_loopback and local_listener
                and not any(name in request.headers for name in proxy_headers))
    except ValueError:
        return False


def access_check(request, settings):
    configured = bool(settings.reviewer_username and settings.reviewer_password)
    if not configured:
        if not settings.hosted and is_loopback(request):
            return None
        return safe_error("REVIEWER_ACCESS_NOT_CONFIGURED", 503)
    if (settings.hosted or not is_loopback(request)) and request.url.scheme != "https":
        return safe_error("HTTPS_REQUIRED", 403)
    try:
        scheme, token = request.headers.get("authorization", "").split(" ", 1)
        if scheme.lower() != "basic":
            raise ValueError
        username, password = base64.b64decode(token, validate=True).decode("utf-8").split(":", 1)
        user_ok = hmac.compare_digest(username.encode(), settings.reviewer_username.encode())
        password_ok = hmac.compare_digest(password.encode(), settings.reviewer_password.encode())
        if user_ok and password_ok:
            return None
    except (ValueError, UnicodeError):
        pass
    return safe_error("REVIEWER_AUTHENTICATION_REQUIRED", 401,
                      {"WWW-Authenticate": 'Basic realm="Pharmacy-AGENT", charset="UTF-8"'})


def create_app(settings=None, *, provider=None, agent_runner=None, push_transport=None, demo_store=None, reviewer_auth=None):
    settings = settings or Settings.load()
    application = FastAPI(title="Pharmacy-AGENT", docs_url=None, redoc_url=None, openapi_url=None)
    application.state.settings = settings
    application.state.provider = provider
    application.state.runner = agent_runner or run_agent
    application.state.last_run = 0.0
    application.state.run_active = False
    application.state.auth_failures = OrderedDict()
    application.state.read_activity = ReadActivity()
    application.state.closing_demo = ClosingDemo()
    application.state.push_sender = PushSender(settings, **({"transport": push_transport} if push_transport else {}))
    application.state.paired_demo = PairedDemo(demo_store or PostgresDemoStore(settings.demo_database_url), application.state.push_sender)
    application.state.reviewer_auth = reviewer_auth or SupabaseReviewerAuth(settings)
    application.state.login_attempts = OrderedDict()
    templates = Jinja2Templates(directory=str(ROOT / "web" / "templates"))

    def return_path(value):
        try: parsed = urlsplit(value)
        except ValueError: return "/demo"
        if parsed.scheme or parsed.netloc or parsed.path not in {nav["path"] for nav in NAVIGATION}:
            return "/demo"
        params = parse_qs(parsed.query)
        order = params.get("order", [""])[0]
        if parsed.path == "/demo" and len(order) == 17 and re.fullmatch(r"demo-[a-f0-9]{12}", order):
            return "/demo?order=" + order + "#order-result"
        return parsed.path

    def paired_service(request):
        service = application.state.paired_demo
        if settings.auth_mode == "supabase":
            return PairedDemo(service.store.for_reviewer(request.state.reviewer_id), service.sender)
        return service

    async def retire_browser(request):
        cookie = request.cookies.get(COOKIE)
        if cookie:
            try:
                await asyncio.to_thread(application.state.paired_demo.store.retire_device, cookie)
            except ClosingError as error:
                if error.status != 403:
                    raise AuthError() from None

    async def personal_access(request):
        if (settings.hosted or not is_loopback(request)) and request.url.scheme != "https":
            return safe_error("HTTPS_REQUIRED", 403)
        public_get = request.method in {"GET", "HEAD"} and request.url.path in {"/login", "/account/setup", "/assets/account-setup.js", "/assets/auth.js", "/assets/pharmacy.css", "/favicon.ico"}
        public_post = request.method == "POST" and request.url.path in {"/api/auth/login", "/api/auth/logout", "/api/auth/setup"}
        if public_get or public_post:
            return None
        auth = application.state.reviewer_auth
        try:
            if not auth.configured:
                raise AuthError("AUTH_NOT_CONFIGURED")
            request.state.reviewer_id = await asyncio.to_thread(auth.store.resolve, request.cookies.get(AUTH_COOKIE))
        except AuthError as error:
            if error.status == 401 and request.method == "GET" and request.url.path in {nav["path"] for nav in NAVIGATION}:
                return RedirectResponse("/login?next=" + quote(return_path(request.url.path + "?" + request.url.query), safe=""), status_code=303)
            return safe_error(error.code, error.status, {"X-Pharmacy-Authentication": "required"} if error.status == 401 else None)
        return None

    @application.middleware("http")
    async def boundaries(request, call_next):
        if settings.auth_mode == "supabase":
            response = await personal_access(request)
        else:
            buckets = application.state.auth_failures
            now = time.monotonic()
            requester = request.client.host if request.client else "unknown"
            # Scope lockout to the actual ASGI requester, never submitted headers.
            failures = buckets.get(requester, deque(maxlen=5))
            while failures and now - failures[0] >= 60:
                failures.popleft()
            # Bounded per-requester/per-worker control. Wider hosting still requires
            # independently verified platform protection and trustworthy proxy behavior.
            if len(failures) >= 5:
                response = safe_error("REVIEWER_AUTH_RATE_LIMITED", 429, {"Retry-After": "60"})
            else:
                response = access_check(request, settings)
                if response is not None and response.status_code == 401 and request.headers.get("authorization"):
                    failures.append(now)
                    buckets[requester] = failures
                    buckets.move_to_end(requester)
                    if len(buckets) > 128:
                        buckets.popitem(last=False)
        if response is None and request.method not in {"GET", "HEAD", "POST"}:
            response = safe_error("METHOD_NOT_ALLOWED", 405)
        if response is None and request.method == "POST":
            origin = request.headers.get("origin")
            if request.url.path in {"/api/auth/login", "/api/auth/logout", "/api/auth/setup"} and not origin:
                response = safe_error("ORIGIN_REQUIRED", 403)
            elif origin and (urlsplit(origin).scheme, urlsplit(origin).netloc) != (request.url.scheme, request.url.netloc):
                response = safe_error("ORIGIN_NOT_ALLOWED", 403)
            elif request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
                response = safe_error("JSON_REQUIRED", 415)
            else:
                body = bytearray()
                try:
                    async with asyncio.timeout(5):
                        async for chunk in request.stream():
                            body.extend(chunk)
                            if len(body) > 32768:
                                response = safe_error("REQUEST_TOO_LARGE", 413)
                                break
                    if response is None:
                        strict_json_loads(bytes(body))
                        request._body = bytes(body)
                except (ContractError, UnicodeError):
                    response = safe_error("INVALID_JSON_CONTRACT")
                except TimeoutError:
                    response = safe_error("REQUEST_BODY_TIMEOUT", 408)
        if response is None:
            try:
                response = await call_next(request)
            except Exception:
                response = safe_error("SERVER_UNAVAILABLE", 503)
        response.headers.update({
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        })
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    application.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Pydantic errors include submitted input; do not serialize those objects.
        return safe_error("INVALID_FORM_INPUT", 422)

    @application.exception_handler(HTTPException)
    async def missing(request, error):
        return safe_error("NOT_FOUND" if error.status_code == 404 else "REQUEST_REJECTED", error.status_code)

    async def page(request: Request):
        entry = next(item for item in NAVIGATION if item["path"] == request.url.path)
        return templates.TemplateResponse(request=request, name="page.html", context={
            "active_view": entry["key"], "navigation": NAVIGATION, "model": settings.model,
            "provider_configured": settings.provider_configured, "source_mode": "fixture", "store_id": 1618,
            "catalog": home_catalog() if entry["key"] == "home" else None,
            "personal_login": settings.auth_mode == "supabase",
        })

    @application.get("/login")
    async def login_page(request: Request):
        return templates.TemplateResponse(request=request, name="login.html", context={
            "active_view": "login", "navigation": [], "return_to": return_path(request.query_params.get("next", "/demo")),
            "auth_configured": settings.auth_mode == "supabase" and application.state.reviewer_auth.configured,
            "personal_login": False,
        })

    @application.post("/api/auth/login")
    async def sign_in(request: Request, body: SignInBody):
        if settings.auth_mode != "supabase":
            return safe_error("AUTH_NOT_CONFIGURED", 503)
        # Separate bounded per-peer/account buckets, never trust forwarded IP headers.
        peer = request.client.host if request.client else "unknown"
        from hashlib import sha256
        key = sha256((peer + "\0" + body.email.casefold()).encode()).hexdigest()
        attempts = application.state.login_attempts
        now = time.monotonic()
        bucket = attempts.setdefault(key, deque(maxlen=5))
        while bucket and now - bucket[0] >= 60:
            bucket.popleft()
        if len(bucket) >= 5:
            return safe_error("AUTH_RATE_LIMITED", 429, {"Retry-After": "60"})
        bucket.append(now); attempts.move_to_end(key)
        while len(attempts) > 128: attempts.popitem(last=False)
        auth = application.state.reviewer_auth
        cookie = None
        try:
            cookie, seconds = await asyncio.to_thread(auth.sign_in, body.email, body.password)
            await retire_browser(request)
            previous = request.cookies.get(AUTH_COOKIE)
            if previous:
                try: await asyncio.to_thread(auth.store.revoke, previous)
                except AuthError as error:
                    if error.status != 401: raise
            response = JSONResponse({"state": "SIGNED_IN", "redirect_to": return_path(body.return_to), "expires_in_seconds": seconds})
            response.set_cookie(AUTH_COOKIE, cookie, max_age=seconds, httponly=True, secure=request.url.scheme == "https", samesite="strict", path="/")
            response.delete_cookie(COOKIE, path="/", httponly=True, secure=request.url.scheme == "https", samesite="strict")
            return response
        except AuthError as error:
            if cookie:
                try: await asyncio.to_thread(auth.store.revoke, cookie)
                except AuthError: pass
            return safe_error(error.code, error.status)

    @application.get("/account/setup")
    async def setup_page(request: Request):
        return templates.TemplateResponse(request=request, name="account-setup.html", context={
            "active_view": "login", "navigation": [], "personal_login": False,
            "auth_configured": settings.auth_mode == "supabase" and application.state.reviewer_auth.configured,
        })

    @application.post("/api/auth/setup")
    async def set_password(request: Request, body: SetupBody):
        if settings.auth_mode != "supabase":
            return safe_error("AUTH_NOT_CONFIGURED", 503)
        peer = request.client.host if request.client else "unknown"
        attempts = application.state.login_attempts
        key = "setup:" + peer
        now = time.monotonic()
        bucket = attempts.setdefault(key, deque(maxlen=5))
        while bucket and now - bucket[0] >= 60:
            bucket.popleft()
        if len(bucket) >= 5:
            return safe_error("AUTH_RATE_LIMITED", 429, {"Retry-After": "60"})
        bucket.append(now); attempts.move_to_end(key)
        while len(attempts) > 128:
            attempts.popitem(last=False)
        try:
            result = await asyncio.to_thread(complete_setup, application.state.reviewer_auth,
                                            body.email, body.token_hash, body.password)
            # Setup does not sign a user in or inherit an old device pairing.
            return JSONResponse(result)
        except AuthError as error:
            return safe_error(error.code, error.status)

    @application.post("/api/auth/logout")
    async def sign_out(request: Request, body: StrictBody):
        if settings.auth_mode != "supabase": return safe_error("AUTH_NOT_CONFIGURED",503)
        try:
            # Retire this device's old subscription before dropping its binding.
            await retire_browser(request)
            cookie=request.cookies.get(AUTH_COOKIE)
            if cookie:
                try: await asyncio.to_thread(application.state.reviewer_auth.store.revoke,cookie)
                except AuthError as error:
                    if error.status != 401: raise
            response=JSONResponse({"state":"SIGNED_OUT"})
            for name in (AUTH_COOKIE,COOKIE):
                response.delete_cookie(name,path="/",httponly=True,secure=request.url.scheme=="https",samesite="strict")
            return response
        except AuthError as error:
            return safe_error(error.code,error.status)

    for entry in NAVIGATION:
        application.add_api_route(entry["path"], page, methods=["GET"], name=entry["key"])

    @application.get("/favicon.ico")
    async def favicon():
        return Response(status_code=204)

    @application.get("/push-worker.js")
    async def push_worker():
        return FileResponse(ROOT / "web/assets/push-worker.js", media_type="application/javascript")

    @application.get("/assets/{filename}")
    async def assets(filename: str):
        paths = {"account-setup.js": ROOT / "web/assets/account-setup.js", "auth.js": ROOT / "web/assets/auth.js", "pharmacy.css": ROOT / "web/assets/pharmacy.css",
                 "closing.js": ROOT / "web/assets/closing.js",
                 "push.js": ROOT / "web/assets/push.js",
                 "pairing.js": ROOT / "web/assets/pairing.js",
                 "pharmacy.js": ROOT / "web/assets/pharmacy.js",
                 "architecture.png": ROOT / "docs/architecture/Pharmacy-Agent-Architecture-Digital.png"}
        if filename not in paths or not paths[filename].is_file():
            return safe_error("NOT_FOUND", 404)
        return FileResponse(paths[filename])

    @application.get("/api/status")
    async def status():
        return {"model": settings.model, "provider_configured": settings.provider_configured,
                "source_mode": "fixture", "store_id": 1618, "read_only": True}

    @application.post("/api/review")
    async def review(body: ReviewBody):
        now = time.monotonic()
        if application.state.run_active or application.state.read_activity.pending:
            return safe_error("REVIEW_ALREADY_RUNNING", 409)
        if now - application.state.last_run < 10:
            return safe_error("REVIEW_RATE_LIMITED", 429, {"Retry-After": "10"})
        application.state.last_run = now
        application.state.run_active = True
        try:
            async with asyncio.timeout(settings.run_seconds + 1):
                return await application.state.runner(body.request, settings=settings,
                    provider=application.state.provider, read_activity=application.state.read_activity)
        except TimeoutError:
            return safe_error("RUN_DEADLINE_EXCEEDED", 504)
        finally:
            application.state.run_active = False

    @application.post("/api/demo")
    async def demo(body: StrictBody):
        def no_fda_network(url, timeout):
            return 404, json.dumps({"error": {"code": "NOT_FOUND"}}).encode()
        report = await asyncio.to_thread(run_review, run_at="2026-10-07T10:00:00-04:00",
                                         inventory_path=LEGACY_FIXTURE_PATH,
                                         fda_http_get=no_fda_network)
        response = envelope(state="Demo", reason="DEMO_FIXED_CLOCK", report=report, settings=settings)
        response["demo"] = {"clock": "2026-10-07T10:00:00-04:00", "model_called": False,
                            "fda_source": "synthetic NO_MATCH fixtures; no live FDA request"}
        return response

    @application.get("/api/test-samples")
    async def samples():
        return {"samples": [{key: sample[key] for key in ("id", "name", "source")} for sample in SAMPLES]}

    def paired_cookie(request):
        return request.cookies.get(COOKIE)

    def device_response(request, cookie, data):
        response = JSONResponse(data)
        response.set_cookie(COOKIE, cookie, max_age=86400, httponly=True,
                            secure=request.url.scheme == "https", samesite="strict", path="/")
        return response

    @application.post("/api/demo-pairing/status")
    async def pairing_status(request: Request, body: StrictBody):
        try:
            return await asyncio.to_thread(paired_service(request).status, paired_cookie(request))
        except ClosingError as error:
            return safe_error(error.code, error.status)

    @application.post("/api/demo-pairing/create")
    async def create_pairing(request: Request, body: StrictBody):
        try:
            if paired_cookie(request):
                raise ClosingError("DEMO_END_CURRENT_PAIRING_FIRST", 409)
            cookie, code = await asyncio.to_thread(paired_service(request).store.create)
            return device_response(request, cookie, {"code": code, "role": "orderer", "expires_in_seconds": 600})
        except ClosingError as error:
            return safe_error(error.code, error.status)

    @application.post("/api/demo-pairing/join")
    async def join_pairing(request: Request, body: PairCodeBody):
        try:
            if paired_cookie(request):
                raise ClosingError("DEMO_END_CURRENT_PAIRING_FIRST", 409)
            cookie = await asyncio.to_thread(paired_service(request).store.join, body.code)
            return device_response(request, cookie, {"role": "manufacturer", "paired": True})
        except ClosingError as error:
            return safe_error(error.code, error.status)

    @application.post("/api/demo-pairing/invite")
    async def renew_pairing(request: Request, body: StrictBody):
        try:
            code = await asyncio.to_thread(paired_service(request).renew_invite, paired_cookie(request))
            return {"code": code, "expires_in_seconds": 600}
        except ClosingError as error:
            return safe_error(error.code, error.status)

    @application.post("/api/demo-pairing/subscription")
    async def pairing_subscription(request: Request, body: PairSubscriptionBody):
        try:
            return await asyncio.to_thread(paired_service(request).register, paired_cookie(request),
                                            body.subscription.model_dump() if body.subscription else None)
        except ClosingError as error:
            return safe_error(error.code, error.status)

    @application.post("/api/demo-pairing/leave")
    async def leave_pairing(request: Request, body: StrictBody):
        try:
            cookie = paired_cookie(request)
            if cookie:
                try:
                    await asyncio.to_thread(paired_service(request).leave, cookie)
                except ClosingError as error:
                    if error.status != 403:
                        raise
            response = JSONResponse({"ended": True})
            response.delete_cookie(COOKIE, path="/", httponly=True, secure=request.url.scheme == "https", samesite="strict")
            return response
        except ClosingError as error:
            return safe_error(error.code, error.status)

    @application.post("/api/demo-pairing/delivery")
    async def confirm_delivery(request: Request, body: DeliveryBody):
        try:
            return await asyncio.to_thread(paired_service(request).delivery, paired_cookie(request), body.order_id)
        except ClosingError as error:
            return safe_error(error.code, error.status)

    @application.post("/api/closing-demo/close")
    async def close_demo(request: Request, body: StrictBody):
        try:
            cookie = paired_cookie(request)
            if cookie:
                return await asyncio.to_thread(paired_service(request).close, cookie)
            return await asyncio.to_thread(application.state.closing_demo.close_day)
        except ClosingError as error:
            return safe_error(error.code, error.status)

    @application.get("/api/push/config")
    async def push_config():
        return application.state.push_sender.configuration()

    @application.post("/api/closing-demo/notify")
    async def notify_demo_order(request: Request, body: PushOrderBody):
        try:
            cookie = paired_cookie(request)
            if cookie:
                return await asyncio.to_thread(paired_service(request).notify, cookie, body.order_id, body.closing_id)
            return await asyncio.to_thread(application.state.closing_demo.notify,
                body.closing_id, body.order_id, body.subscription.model_dump(), application.state.push_sender)
        except ClosingError as error:
            return safe_error(error.code, error.status)

    @application.post("/api/closing-demo/submit")
    async def submit_demo_order(request: Request, body: DemoOrderBody):
        try:
            cookie = paired_cookie(request)
            if cookie:
                return await asyncio.to_thread(paired_service(request).submit, cookie,
                    body.closing_id, body.submission_id, [line.model_dump() for line in body.lines])
            return await asyncio.to_thread(application.state.closing_demo.submit,
                body.closing_id, body.submission_id, [line.model_dump() for line in body.lines])
        except ClosingError as error:
            return safe_error(error.code, error.status)

    @application.post("/api/test-input")
    async def tester(body: TesterBody):
        sample = next((sample for sample in SAMPLES if sample["id"] == body.sample_id), None)
        if sample is None:
            return safe_error("UNKNOWN_TEST_SAMPLE", 422)
        test_request = deepcopy({key: value for key, value in sample.items() if key not in {"id", "name"}})
        if body.request_text is not None:
            test_request = {"source": "user_request", "payload": {"request": body.request_text}}
        test_request["output_change"] = body.output_change
        try:
            return run_demo(test_request)
        except ContractError:
            return safe_error("INVALID_TEST_INPUT", 422)

    @application.post("/api/failure-preview")
    async def failure(body: FailureBody):
        title, detail, recovery = FAILURES[body.scenario]
        return {"scenario": body.scenario, "title": title, "detail": detail,
                "recovery": recovery, "simulated": True}

    return application

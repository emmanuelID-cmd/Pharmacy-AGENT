"""Server-only configuration. Values are never included in browser diagnostics."""
from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "claude-sonnet-5-5"
SUPPORTED_MODEL_PREFIXES = ("claude-haiku-", "claude-sonnet-")
CONFIG_NAMES = {
    "APP_ENV", "ANTHROPIC_API_KEY", "ANTHOPIC_API_KEY", "ANTHROPIC_MODEL",
    "PHARMACY_REVIEWER_USERNAME", "PHARMACY_REVIEWER_PASSWORD", "PHARMACY_ALLOWED_HOSTS",
    "PHARMACY_PUSH_PRIVATE_KEY", "PHARMACY_PUSH_SUBJECT", "PHARMACY_DEMO_DATABASE_URL",
    "PHARMACY_AUTH_MODE", "PHARMACY_AUTH_DATABASE_URL", "SUPABASE_URL",
    "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_PUBLISABLE_KEY",
}


@dataclass(frozen=True)
class Settings:
    model: str = DEFAULT_MODEL
    api_key: str = field(default="", repr=False)
    app_env: str = "development"
    reviewer_username: str = field(default="", repr=False)
    reviewer_password: str = field(default="", repr=False)
    auth_mode: str = "basic"
    auth_database_url: str = field(default="", repr=False)
    supabase_url: str = field(default="", repr=False)
    supabase_publishable_key: str = field(default="", repr=False)
    demo_database_url: str = field(default="", repr=False)
    push_private_key: str = field(default="", repr=False)
    push_subject: str = "https://github.com/emmanuelID-cmd/Pharmacy-AGENT"
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "[::1]")
    run_seconds: float = 120
    model_seconds: float = 90
    max_turns: int = 6
    max_tokens: int = 24576

    def __post_init__(self):
        if self.auth_mode not in {"basic", "supabase"}:
            raise ValueError("INVALID_AUTH_MODE")
        if not self.model.startswith(SUPPORTED_MODEL_PREFIXES) or len(self.model) > 100:
            raise ValueError("SUPPORTED_CLAUDE_MODEL_REQUIRED")
        if not 0 < self.run_seconds <= 120 or not 0 < self.model_seconds <= min(self.run_seconds, 90):
            raise ValueError("INVALID_AGENT_DEADLINE")
        if not 1 <= self.max_turns <= 6 or not 512 <= self.max_tokens <= 24576:
            raise ValueError("INVALID_MODEL_BUDGET")

    @property
    def hosted(self):
        return self.app_env != "development"

    @property
    def provider_configured(self):
        return bool(self.api_key)

    @classmethod
    def load(cls, root=ROOT):
        values = {}

        def apply_layer(layer):
            values.update(layer)
            if "SUPABASE_PUBLISHABLE_KEY" in layer or "SUPABASE_PUBLISABLE_KEY" in layer:
                values["supabase_key"] = layer.get("SUPABASE_PUBLISHABLE_KEY", layer.get("SUPABASE_PUBLISABLE_KEY", ""))
            # Resolve spellings within a layer, then apply layer precedence.
            # An OS alias must not lose to a canonical name in an older file.
            if "ANTHROPIC_API_KEY" in layer or "ANTHOPIC_API_KEY" in layer:
                values["provider_key"] = (layer["ANTHROPIC_API_KEY"] if "ANTHROPIC_API_KEY" in layer
                                          else layer.get("ANTHOPIC_API_KEY", ""))

        for name in (".env", ".env.push", ".env.demo", ".env.auth", ".env.local", ".env.web"):
            path = root / name
            if path.is_file():
                apply_layer({k: v for k, v in dotenv_values(path, interpolate=False).items()
                             if k in CONFIG_NAMES and v is not None})
        apply_layer({k: os.environ[k] for k in CONFIG_NAMES if k in os.environ})
        hosted = bool(os.environ.get("VERCEL"))
        hosts = ["localhost", "127.0.0.1", "[::1]"]
        if os.environ.get("VERCEL_URL"):
            hosts.append(os.environ["VERCEL_URL"])
        if values.get("PHARMACY_ALLOWED_HOSTS"):
            hosts = [v.strip() for v in values["PHARMACY_ALLOWED_HOSTS"].split(",") if v.strip()]
        app_env = "production" if hosted else values.get("APP_ENV", "development")
        return cls(
            model=values.get("ANTHROPIC_MODEL") or DEFAULT_MODEL,
            api_key=values.get("provider_key", ""),
            app_env=app_env,
            run_seconds=50 if app_env != "development" else 120,
            model_seconds=45 if app_env != "development" else 90,
            reviewer_username=values.get("PHARMACY_REVIEWER_USERNAME", ""),
            reviewer_password=values.get("PHARMACY_REVIEWER_PASSWORD", ""),
            auth_mode=values.get("PHARMACY_AUTH_MODE") or "basic",
            auth_database_url=values.get("PHARMACY_AUTH_DATABASE_URL", ""),
            supabase_url=values.get("SUPABASE_URL", ""),
            supabase_publishable_key=values.get("supabase_key", ""),
            demo_database_url=values.get("PHARMACY_DEMO_DATABASE_URL", ""),
            push_private_key=values.get("PHARMACY_PUSH_PRIVATE_KEY", ""),
            push_subject=values.get("PHARMACY_PUSH_SUBJECT") or "https://github.com/emmanuelID-cmd/Pharmacy-AGENT",
            allowed_hosts=tuple(hosts),
        )

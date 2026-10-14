"""Server-only configuration. Values are never included in browser diagnostics."""
from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
LATEST_HAIKU = "claude-haiku-5-5"
CONFIG_NAMES = {
    "APP_ENV", "ANTHROPIC_API_KEY", "ANTHOPIC_API_KEY", "ANTHROPIC_MODEL",
    "PHARMACY_REVIEWER_USERNAME", "PHARMACY_REVIEWER_PASSWORD", "PHARMACY_ALLOWED_HOSTS",
}


@dataclass(frozen=True)
class Settings:
    model: str = LATEST_HAIKU
    api_key: str = field(default="", repr=False)
    app_env: str = "development"
    reviewer_username: str = field(default="", repr=False)
    reviewer_password: str = field(default="", repr=False)
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "[::1]")
    run_seconds: float = 50
    model_seconds: float = 15
    max_turns: int = 6
    max_tokens: int = 8192

    def __post_init__(self):
        if not self.model.startswith("claude-haiku-") or len(self.model) > 100:
            raise ValueError("HAIKU_MODEL_REQUIRED")
        if not 0 < self.run_seconds <= 50 or not 0 < self.model_seconds <= self.run_seconds:
            raise ValueError("INVALID_AGENT_DEADLINE")
        if not 1 <= self.max_turns <= 6 or not 512 <= self.max_tokens <= 8192:
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
            # Resolve spellings within a layer, then apply layer precedence.
            # An OS alias must not lose to a canonical name in an older file.
            if "ANTHROPIC_API_KEY" in layer or "ANTHOPIC_API_KEY" in layer:
                values["provider_key"] = (layer["ANTHROPIC_API_KEY"] if "ANTHROPIC_API_KEY" in layer
                                          else layer.get("ANTHOPIC_API_KEY", ""))

        for name in (".env", ".env.local", ".env.web"):
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
        return cls(
            model=values.get("ANTHROPIC_MODEL") or LATEST_HAIKU,
            api_key=values.get("provider_key", ""),
            app_env="production" if hosted else values.get("APP_ENV", "development"),
            reviewer_username=values.get("PHARMACY_REVIEWER_USERNAME", ""),
            reviewer_password=values.get("PHARMACY_REVIEWER_PASSWORD", ""),
            allowed_hosts=tuple(hosts),
        )

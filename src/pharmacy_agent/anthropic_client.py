"""Explicit Claude SDK adapter; no automatic tool execution or raw streaming."""
import asyncio
from copy import deepcopy

from anthropic import APITimeoutError, AsyncAnthropic, AuthenticationError, NotFoundError, RateLimitError

from ..pharmacy_tools.instructions import SYSTEM_PROMPT, TOOL_SPECS


class ProviderUnavailable(Exception):
    """A fixed safe code replaces SDK exceptions that may contain private details."""
    def __init__(self, code="PROVIDER_UNAVAILABLE"):
        self.code = code
        super().__init__(code)


def claude_tools():
    """Preserve the historical preview's single-NDC reads using the batch item's schema."""
    specs = {spec["function"]["name"]: spec["function"] for spec in TOOL_SPECS}
    inventory = specs["read_store_inventory"]
    batch = specs["get_fda_shortage_context_batch"]
    return [{"name": inventory["name"], "description": inventory["description"],
             "input_schema": deepcopy(inventory["parameters"])},
            {"name": "get_fda_shortage_context",
             "description": "Read national FDA shortage context for one exact trusted package NDC. Read-only.",
             "input_schema": {"type": "object", "properties": {
                 "package_ndc": deepcopy(batch["parameters"]["properties"]["package_ndcs"]["items"])},
                 "required": ["package_ndc"], "additionalProperties": False}}]


def preview_system_prompt():
    """Reuse shared safety/output rules with the preview's historical tool declaration."""
    start = SYSTEM_PROMPT.index("TOOLS (read-only, the only two that exist):")
    end = SYSTEM_PROMPT.index("No other tool exists.", start)
    declaration = ("HISTORICAL WEB PREVIEW: the original 20-row synthetic fixture, not the 150-row catalog.\n"
                   "TOOLS (read-only, the only two that exist):\n"
                   "1. read_store_inventory(store_id=1618): call it exactly once, first.\n"
                   "2. get_fda_shortage_context(package_ndc): call once per distinct package NDC from the trusted context, "
                   "each identifier exactly as written. Never guess, reformat or invent an NDC.\n")
    return SYSTEM_PROMPT[:start] + declaration + SYSTEM_PROMPT[end:]


class ClaudeClient:
    def __init__(self, settings):
        self.settings = settings

    async def complete(self, *, messages, tools, choice, timeout):
        if not self.settings.api_key:
            raise ProviderUnavailable("PROVIDER_NOT_CONFIGURED")
        kwargs = dict(model=self.settings.model, max_tokens=self.settings.max_tokens,
                      system=preview_system_prompt(), messages=deepcopy(messages),
                      thinking={"type": "disabled"})
        if tools:
            kwargs.update(tools=deepcopy(tools), tool_choice=choice)
        try:
            # Pin the provider host. Unrelated environment variables cannot redirect
            # the key; retries are zero because the outer run owns the deadline.
            async with AsyncAnthropic(api_key=self.settings.api_key,
                                      base_url="https://api.anthropic.com",
                                      timeout=timeout, max_retries=0) as client:
                async with asyncio.timeout(timeout):
                    response = await client.messages.create(**kwargs)
            return response.model_dump(mode="json", exclude_none=True)
        except AuthenticationError:
            raise ProviderUnavailable("PROVIDER_AUTHENTICATION_FAILED") from None
        except NotFoundError:
            raise ProviderUnavailable("MODEL_NOT_AVAILABLE") from None
        except RateLimitError:
            raise ProviderUnavailable("PROVIDER_RATE_LIMITED") from None
        except (APITimeoutError, TimeoutError):
            raise ProviderUnavailable("MODEL_TIMEOUT") from None
        except Exception:
            raise ProviderUnavailable() from None

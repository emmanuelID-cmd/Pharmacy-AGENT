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
    return [{"name": spec["function"]["name"],
             "description": spec["function"]["description"],
             "input_schema": deepcopy(spec["function"]["parameters"])} for spec in TOOL_SPECS]


class ClaudeClient:
    def __init__(self, settings):
        self.settings = settings

    async def complete(self, *, messages, tools, choice, timeout):
        if not self.settings.api_key:
            raise ProviderUnavailable("PROVIDER_NOT_CONFIGURED")
        kwargs = dict(model=self.settings.model, max_tokens=self.settings.max_tokens,
                      system=SYSTEM_PROMPT, messages=deepcopy(messages),
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

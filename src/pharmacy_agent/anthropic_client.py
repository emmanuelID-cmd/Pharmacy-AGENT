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
    """Copy the shared inventory/batched-FDA read contracts for the provider."""
    return [{"name": spec["function"]["name"], "description": spec["function"]["description"],
             "input_schema": deepcopy(spec["function"]["parameters"])} for spec in TOOL_SPECS]


def preview_system_prompt():
    """Reuse pinned safety rules and specify the bounded catalog review schedule."""
    return ("CATALOG REVIEW: 150 public product identities linked to synthetic stock.\n"
            "After inventory, request all remaining FDA reads in the same turn, using distinct groups of up to "
            "ten package NDCs (at most fifteen groups). Never repeat an NDC. After the tool results, copy the "
            "supplied compact report JSON exactly, without prose, markdown or added whitespace.\n\n" + SYSTEM_PROMPT)


def sonnet_tools(tools):
    """Build strict Sonnet schemas; trusted runtime guards enforce batch limits."""
    prepared = deepcopy(tools)
    unsupported_schema_keys = ("minItems", "maxItems", "uniqueItems", "pattern")
    for spec in prepared:
        spec["strict"] = True
        pending = [spec["input_schema"]]
        while pending:
            node = pending.pop()
            if isinstance(node, dict):
                for key in unsupported_schema_keys:
                    node.pop(key, None)
                pending.extend(value for value in node.values() if isinstance(value, (dict, list)))
            elif isinstance(node, list):
                pending.extend(node)
    return prepared


class ClaudeClient:
    def __init__(self, settings):
        self.settings = settings

    async def complete(self, *, messages, tools, choice, timeout):
        if not self.settings.api_key:
            raise ProviderUnavailable("PROVIDER_NOT_CONFIGURED")
        is_sonnet = self.settings.model.startswith("claude-sonnet-")
        thinking_type = "between_tools" if is_sonnet else "disabled"
        kwargs = dict(model=self.settings.model, max_tokens=min(self.settings.max_tokens, 4096) if tools else self.settings.max_tokens,
                      system=preview_system_prompt(), messages=deepcopy(messages),
                      thinking={"type": thinking_type})
        if is_sonnet and not tools:
            # The final turn copies a trusted report; low effort keeps the large
            # exact-copy response within the configured model deadline.
            kwargs["output_config"] = {"effort": "low"}
        if tools:
            if is_sonnet:
                # Sonnet 5.5 rejects forced selection and several JSON Schema array
                # constraints. Strict shapes remain; the runtime guard enforces
                # NDC format, uniqueness, and batch size before any read dispatch.
                kwargs.update(tools=sonnet_tools(tools), tool_choice={"type": "auto"})
            else:
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

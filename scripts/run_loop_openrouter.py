"""Run the real agent loop (observe -> decide -> act -> feed back) with an OpenRouter model.

The team's loop (src/pharmacy_agent/runtime.py run_agent) speaks the Anthropic Messages
format and defaults to Claude Sonnet. This script only swaps the provider: an adapter
translates each turn to OpenRouter's OpenAI-compatible chat API, so any OpenRouter model
with tool calling can make the decisions. Tools, guards, calculations and report
validation are the unchanged team code.

Usage (key read from the environment, never printed):
  OPENROUTER_API_KEY=... python scripts/run_loop_openrouter.py
  OPENROUTER_API_KEY=... python scripts/run_loop_openrouter.py --model openrouter/free --catalog
"""
import argparse
import asyncio
import json
import os
import re
import sys
import urllib.error
import urllib.request
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pharmacy_agent.anthropic_client import ProviderUnavailable, preview_system_prompt  # noqa: E402
from src.pharmacy_agent.config import Settings  # noqa: E402
from src.pharmacy_agent.runtime import run_agent  # noqa: E402
from src.pharmacy_tools.fda import _ssl_context  # noqa: E402
from src.pharmacy_tools.inventory import LEGACY_FIXTURE_PATH, read_store_inventory  # noqa: E402

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "liquid/lfm-2.5-2.6b:free"


def to_openai_messages(messages):
    """Anthropic-format turns from run_agent -> OpenAI chat messages."""
    out = [{"role": "system", "content": preview_system_prompt()}]
    for message in messages:
        content = message["content"]
        if isinstance(content, str):
            out.append({"role": message["role"], "content": content})
        elif message["role"] == "assistant":
            out.append({"role": "assistant", "content": None, "tool_calls": [
                {"id": block["id"], "type": "function",
                 "function": {"name": block["name"], "arguments": json.dumps(block["input"])}}
                for block in content if block.get("type") == "tool_use"]})
        else:
            out.extend({"role": "tool", "tool_call_id": block["tool_use_id"], "content": block["content"]}
                       for block in content if block.get("type") == "tool_result")
    return out


def provider_schema(schema):
    """Drop JSON Schema keywords some OpenRouter providers reject (uniqueItems).

    Safe: run_agent and the guard still reject repeated or unlisted NDCs themselves.
    """
    if isinstance(schema, dict):
        return {k: provider_schema(v) for k, v in schema.items() if k != "uniqueItems"}
    if isinstance(schema, list):
        return [provider_schema(v) for v in schema]
    return schema


def to_openai_choice(choice):
    if choice is None:
        return None
    if choice.get("type") == "tool":
        return {"type": "function", "function": {"name": choice["name"]}}
    return "required"


class OpenRouterProvider:
    """Same async complete() contract as ClaudeClient, logging each decision."""

    def __init__(self, key, model, log):
        self.key, self.model, self.log = key, model, log
        self.ids = {}
        self.trace = []

    def _safe_id(self, raw):
        # run_agent only accepts [A-Za-z0-9_-]{1,128}; keep a stable mapping per run
        if raw not in self.ids:
            self.ids[raw] = f"call_{len(self.ids) + 1}"
        return self.ids[raw]

    def _post(self, body, timeout):
        request = urllib.request.Request(OPENROUTER_URL, data=json.dumps(body).encode(), method="POST",
                                         headers={"Authorization": f"Bearer {self.key}",
                                                  "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
                return json.loads(response.read(2_000_000))
        except urllib.error.HTTPError as error:
            code = {401: "PROVIDER_AUTHENTICATION_FAILED", 404: "MODEL_NOT_AVAILABLE",
                    429: "PROVIDER_RATE_LIMITED"}.get(error.code, "PROVIDER_UNAVAILABLE")
            raise ProviderUnavailable(code) from None
        except (TimeoutError, OSError):
            raise ProviderUnavailable("MODEL_TIMEOUT") from None
        except ValueError:
            raise ProviderUnavailable() from None

    async def complete(self, *, messages, tools, choice, timeout):
        body = {"model": self.model, "messages": to_openai_messages(messages), "max_tokens": 8192}
        if tools:
            body["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                               "parameters": provider_schema(t["input_schema"])}}
                             for t in tools]
            body["tool_choice"] = to_openai_choice(choice)
        offered = [t["name"] for t in tools] or ["(none: write the final report)"]
        turn = {"turn": len(self.trace) + 1, "model_input": body}
        self.trace.append(turn)
        data = await asyncio.to_thread(self._post, body, timeout)
        turn["model_output_raw"] = data
        if not isinstance(data, dict) or not data.get("choices"):
            raise ProviderUnavailable()
        message = data["choices"][0].get("message") or {}
        finish = data["choices"][0].get("finish_reason")
        calls = message.get("tool_calls") or []
        if calls:
            blocks = []
            for call in calls:
                try:
                    arguments = json.loads(call["function"].get("arguments") or "{}")
                except ValueError:
                    arguments = None
                blocks.append({"type": "tool_use", "id": self._safe_id(call.get("id", "")),
                               "name": call["function"].get("name"), "input": arguments})
            self.log.append(("DECIDE", offered, [f"{b['name']}({json.dumps(b['input'])[:80]})" for b in blocks]))
            return {"content": blocks, "stop_reason": "tool_use"}
        text = message.get("content") or ""
        self.log.append(("DECIDE", offered, [f"final text, {len(text)} chars"]))
        return {"content": [{"type": "text", "text": text}] if text else [],
                "stop_reason": "end_turn" if finish in ("stop", "end_turn", None) else "max_tokens"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model id with tool calling")
    parser.add_argument("--catalog", action="store_true", help="use the 150-item catalog instead of the 20-row fixture")
    parser.add_argument("--fixture", help="inventory JSON to use instead of the 20-row fixture (eval cases)")
    parser.add_argument("--trace", help="write the full trace (model inputs, raw tool results, model outputs, final report) to this JSON file")
    parser.add_argument("--run-at", default="2026-10-07T10:00:00-04:00",
                        help="review time; defaults to the fixture's snapshot day so data is fresh ('now' = real clock)")
    args = parser.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is missing.")

    log = []
    provider = OpenRouterProvider(key, args.model, log)
    path = args.fixture or LEGACY_FIXTURE_PATH
    reader = None if args.catalog and not args.fixture else partial(read_store_inventory, path=path)
    settings = Settings(api_key="openrouter-adapter")  # run limits: 6 turns, 120 s, 90 s per model call
    result = asyncio.run(run_agent("Run the inventory review for store 1618.", settings=settings,
                                   provider=provider, inventory_reader=reader,
                                   run_at=None if args.run_at == "now" else args.run_at))

    print(f"Model: {args.model} | data: {'150-item catalog' if args.catalog else '20-row synthetic fixture'} | run_at: {args.run_at}")
    for step, (_, offered, decision) in enumerate(log, 1):
        print(f"Step {step}: offered {offered} -> model decided {decision}")
    agent = dict(result["agent"], model=args.model)
    print("\nFINAL:", json.dumps({"state": result["state"], "reason_code": result["reason_code"], "agent": agent}))
    report = result.get("report")
    if args.trace:
        trace = {"model": args.model, "fixture": str(path), "run_at": args.run_at, "turns": provider.trace,
                 "final": {"state": result["state"], "reason_code": result["reason_code"],
                           "agent": dict(result["agent"], model=args.model), "report": report}}
        Path(args.trace).write_text(json.dumps(trace, indent=1, ensure_ascii=False))
        print("trace saved:", args.trace)
    if report:
        print("run_state:", report.get("run_state"), "| warnings:", report.get("warning_codes"))
        classes = {}
        for item in report.get("items", []):
            classes[item.get("local_class")] = classes.get(item.get("local_class"), 0) + 1
        print("item classes:", classes)


if __name__ == "__main__":
    main()

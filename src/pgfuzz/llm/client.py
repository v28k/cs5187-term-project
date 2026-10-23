"""Model access for the LLM arm, with every response stored for replay.

Modes:

``api``     call Claude through the Anthropic SDK (``pip install anthropic``; credentials
            from ``ANTHROPIC_API_KEY`` or an ``ant auth login`` profile).
``manual``  write the prompt to ``<dir>/prompts/<key>.md`` and stop; paste it into Claude,
            save the JSON answer as ``<dir>/responses/<key>.json``, and run again.
            No API key needed.
either      a response file that already exists is reused (replay): reruns are
            reproducible and cost nothing, and the paper's numbers can be regenerated.

Token usage of every API call is stored with the response, so the ledger can
report the cost of the arm (RQ4).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pgfuzz.llm.prompt import RESPONSE_SCHEMA

DEFAULT_MODEL = "claude-opus-5-5"
# USD per million tokens (Anthropic first-party API, October 2026): input, output, cache read, cache write (5 min).
PRICES = {"claude-opus-5-5": (4.00, 20.00, 0.20, 5.00), "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
          "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125)}


class NeedsManualResponse(Exception):
    """Manual mode: the prompt was written; a response file is needed to continue."""


@dataclass
class Reply:
    data: dict[str, Any]
    usage: dict[str, int]
    cost_usd: float
    cached: bool
    model: str


def cost(model: str, usage: dict[str, int]) -> float:
    p_in, p_out, p_cr, p_cw = PRICES.get(model, PRICES[DEFAULT_MODEL])
    return round((usage.get("input_tokens", 0) * p_in + usage.get("output_tokens", 0) * p_out
                  + usage.get("cache_read_input_tokens", 0) * p_cr
                  + usage.get("cache_creation_input_tokens", 0) * p_cw) / 1e6, 5)


class LLMClient:
    def __init__(self, workdir: str | Path, mode: str = "api", model: str = DEFAULT_MODEL, effort: str = "high",
                 max_tokens: int = 16000) -> None:
        if mode not in ("api", "manual"):
            raise ValueError("mode must be 'api' or 'manual'")
        self.dir = Path(workdir)
        self.mode, self.model, self.effort, self.max_tokens = mode, model, effort, max_tokens
        (self.dir / "responses").mkdir(parents=True, exist_ok=True)
        (self.dir / "prompts").mkdir(parents=True, exist_ok=True)
        self._client: Any = None

    def ask(self, key: str, system: str, messages: list[dict[str, Any]]) -> Reply:
        resp_file = self.dir / "responses" / f"{key}.json"
        if resp_file.exists():
            rec = json.loads(resp_file.read_text(encoding="utf-8"))
            data = rec.get("data", rec)          # manual answers may be the bare JSON object
            usage = rec.get("usage", {})
            return Reply(_validate(data), usage, rec.get("cost_usd", 0.0), True, rec.get("model", "manual"))
        if self.mode == "manual":
            self._write_prompt(key, system, messages)
            raise NeedsManualResponse(str(self.dir / "prompts" / f"{key}.md"))
        data, usage = self._call(system, messages)
        c = cost(self.model, usage)
        resp_file.write_text(json.dumps({"model": self.model, "effort": self.effort, "usage": usage, "cost_usd": c,
                                         "data": data, "t": time.time()}, indent=1), encoding="utf-8")
        return Reply(_validate(data), usage, c, False, self.model)

    def _write_prompt(self, key: str, system: str, messages: list[dict[str, Any]]) -> None:
        parts = ["<!-- Paste everything below into Claude. Save its JSON answer as "
                 f"responses/{key}.json -->", "## Instructions", system]
        for m in messages:
            parts += [f"## {m['role']}", m["content"] if isinstance(m["content"], str) else json.dumps(m["content"])]
        parts += ["## Output format", "Answer with one JSON object matching this schema, nothing else:",
                  "```json", json.dumps(RESPONSE_SCHEMA, indent=1), "```"]
        (self.dir / "prompts" / f"{key}.md").write_text("\n\n".join(parts), encoding="utf-8")

    def _call(self, system: str, messages: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, int]]:
        import anthropic

        if self._client is None:
            self._client = anthropic.Anthropic()
        for attempt in range(4):
            try:
                response = self._client.beta.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                    system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                    messages=messages,
                    output_config={"effort": self.effort,
                                   "format": {"type": "json_schema", "schema": RESPONSE_SCHEMA}},
                )
                break
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                if attempt == 3:
                    raise
                time.sleep(15 * (attempt + 1))
        if response.stop_reason == "refusal":
            raise RuntimeError(f"model refused: {getattr(response.stop_details, 'category', None)}")
        text = next((b.text for b in response.content if b.type == "text"), "")
        u = response.usage
        usage = {k: int(getattr(u, k, 0) or 0) for k in ("input_tokens", "output_tokens",
                                                         "cache_read_input_tokens", "cache_creation_input_tokens")}
        return json.loads(text), usage


def _validate(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("response is not a JSON object")
    out = {"rationale": str(data.get("rationale", "")), "grammar_fragment": str(data.get("grammar_fragment", "")),
           "seeds": [str(s) for s in data.get("seeds", []) if str(s).strip()],
           "features": [str(f) for f in data.get("features", [])],
           "rewrites": [r for r in data.get("rewrites", []) if isinstance(r, dict) and r.get("template")]}
    return out

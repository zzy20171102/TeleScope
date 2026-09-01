"""LLM backend abstraction: deterministic RuleBackend (offline default) +
OpenAI-compatible backend (env-configured). Factor 1/4: structured outputs."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class RuleBackend:
    """Deterministic offline backend; dispatches by prompt name."""

    name = "rule"

    def complete_json(self, prompt_name: str, context: dict[str, Any]) -> dict[str, Any]:
        from . import rules

        return rules.dispatch(prompt_name, context)


class OpenAICompatBackend:
    """OpenAI-compatible chat completions with JSON response format.

    Tested against MiniMax (minimax-m3). The model may emit <think> reasoning
    before the JSON object; `extract_json` handles that tolerantly.
    """

    name = "openai-compat"

    def __init__(self, api_key: str, base_url: str, model: str,
                 timeout: int = 180, temperature: float = 0.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature

    def complete_json(self, prompt_name: str, context: dict[str, Any]) -> dict[str, Any]:
        from ..config import load_prompt

        template = load_prompt(prompt_name)
        for k, v in context.items():
            template = template.replace("{{ " + k + " }}", str(v))
            template = template.replace("{{" + k + "}}", str(v))
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": template}],
        }
        try:
            data = self._post(payload)
        except urllib.error.HTTPError as e:
            # some providers reject response_format -> retry without it
            if e.code in (400, 404, 422):
                payload.pop("response_format", None)
                data = self._post(payload)
            else:
                raise
        msg = data["choices"][0]["message"]
        content = (msg.get("content") or msg.get("reasoning_content") or "").strip()
        if not content:
            raise ValueError("empty content from LLM")
        return extract_json(content)

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


def extract_json(text: str) -> dict[str, Any]:
    """Tolerant JSON extraction: strips <think> blocks, markdown fences and
    stray text around the JSON object (e.g. minimax-m3 reasoning output)."""
    t = text.strip()
    if "</think>" in t:
        t = t.rsplit("</think>", 1)[1].strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t[:4].lower() == "json":
            t = t[4:]
        t = t.strip()
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object in LLM output: {text[:200]!r}")
    return json.loads(t[start:end + 1])


def get_backend() -> "RuleBackend | OpenAICompatBackend":
    from .. import config

    config.load_env_file()
    key = os.environ.get("TELESCOPE_LLM_API_KEY", "")
    if key:
        base = os.environ.get("TELESCOPE_LLM_BASE_URL", "https://api.minimax.cn/v1")
        model = os.environ.get("TELESCOPE_LLM_MODEL", "minimax-m3")
        return OpenAICompatBackend(key, base, model)
    return RuleBackend()

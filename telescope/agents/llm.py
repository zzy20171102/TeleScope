"""LLM backend abstraction: deterministic RuleBackend (offline default) +
OpenAI-compatible backend (env-configured). Factor 1/4: structured outputs.

P0/T1.3+: three-layer JSON robustness against malformed model output:
1) strict parse; 2) unescaped-quote repair (state machine); 3) one retry
with a strict-JSON instruction appended. Real exception details are kept
for error_card audit (Factor 9).
"""
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
    before the JSON object and occasionally unescaped quotes inside string
    values; both are handled tolerantly.
    """

    name = "openai-compat"

    def __init__(self, api_key: str, base_url: str, model: str,
                 timeout: int = 180, temperature: float = 0.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.last_error: str = ""

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
        }

        def _call(tpl: str) -> str:
            payload["messages"] = [{"role": "user", "content": tpl}]
            try:
                data = self._post(payload)
            except urllib.error.HTTPError as e:
                # some providers reject response_format -> retry without it
                if e.code in (400, 404, 422) and "response_format" in payload:
                    payload.pop("response_format", None)
                    data = self._post(payload)
                else:
                    raise
            msg = data["choices"][0]["message"]
            content = (msg.get("content") or msg.get("reasoning_content") or "").strip()
            if not content:
                raise ValueError("empty content from LLM")
            return content

        self.last_error = ""
        content = _call(template)
        try:
            return extract_json(content)
        except ValueError as e1:
            try:
                return extract_json(content, repair=True)
            except ValueError as e2:
                self.last_error = f"json: {e2}"[:200]
        # one strict retry
        strict = (template + "\n\n注意：输出必须是严格合法的 JSON；字符串值内部不得出现"
                  "未转义的双引号（可改用单引号或中文引号）。")
        try:
            content2 = _call(strict)
            return extract_json(content2, repair=True)
        except ValueError as e3:
            self.last_error = f"{type(e3).__name__}: {e3}"[:200]
            raise

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


def _fix_unescaped_quotes(s: str) -> str:
    """Escape ASCII double quotes that appear inside JSON string values.

    Heuristic state machine: a quote is treated as the string terminator only
    when the next non-space char is one of `,}]:` or end-of-input; otherwise
    it is escaped. Fixes e.g. {"a": "He said "stop" loudly", "b": 1}.
    """
    out: list[str] = []
    in_str = False
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch == "\\" and in_str and i + 1 < n:
            out.append(ch)
            out.append(s[i + 1])
            i += 2
            continue
        if ch == '"':
            if not in_str:
                in_str = True
                out.append(ch)
            else:
                j = i + 1
                while j < n and s[j] in " \t\r\n":
                    j += 1
                if j >= n or s[j] in ",}]:":
                    in_str = False
                    out.append(ch)
                else:
                    out.append('\\"')
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def extract_json(text: str, repair: bool = False) -> dict[str, Any]:
    """Tolerant JSON extraction: strips <think> blocks, markdown fences and
    stray text around the JSON object (e.g. minimax-m3 reasoning output).
    With repair=True, retries parse after fixing unescaped inner quotes."""
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
    raw = t[start:end + 1]
    try:
        return json.loads(raw)
    except ValueError:
        if not repair:
            raise
    return json.loads(_fix_unescaped_quotes(raw))


def get_backend() -> "RuleBackend | OpenAICompatBackend":
    from .. import config

    config.load_env_file()
    key = os.environ.get("TELESCOPE_LLM_API_KEY", "")
    if key:
        base = os.environ.get("TELESCOPE_LLM_BASE_URL", "https://api.minimax.cn/v1")
        model = os.environ.get("TELESCOPE_LLM_MODEL", "minimax-m3")
        return OpenAICompatBackend(key, base, model)
    return RuleBackend()

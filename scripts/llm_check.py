"""Live LLM connectivity check for TeleScope (manual, network required).

Usage (from repo root):
    python -X utf8 scripts/llm_check.py              # connectivity + structured output
    python -X utf8 scripts/llm_check.py --pipeline   # also run full daily pipeline
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_env():
    import os

    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() and k.strip() not in os.environ:
                os.environ[k.strip()] = v.strip().strip('"').strip("'")
    return os.environ


def extract_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t[:4].lower() == "json":
            t = t[4:]
        t = t.strip()
    s, e = t.find("{"), t.rfind("}")
    if s == -1 or e <= s:
        raise ValueError(f"no JSON object in output: {text[:200]!r}")
    return json.loads(t[s:e + 1])


def main() -> int:
    env = load_env()
    key = env.get("TELESCOPE_LLM_API_KEY", "")
    base = env.get("TELESCOPE_LLM_BASE_URL", "https://api.minimax.cn/v1").rstrip("/")
    model = env.get("TELESCOPE_LLM_MODEL", "minimax-m3")
    if not key:
        print("[skip] TELESCOPE_LLM_API_KEY not set; nothing to check")
        return 0
    print(f"base={base}  model={model}  key={key[:8]}...{key[-4:]} (len={len(key)})")

    cards = [{"id": 1, "title": "Russia launches missile strike on Kyiv",
              "text": "Multiple explosions reported; air defense active."},
             {"id": 2, "title": "Local cake festival draws crowds",
              "text": "A baking contest was held downtown."}]
    prompt = (ROOT / "prompts" / "screener.md.j2").read_text(encoding="utf-8")
    prompt = prompt.replace("{{ items_json }}",
                            json.dumps(cards, ensure_ascii=False))
    payload_base = {"model": model, "temperature": 0.0,
                    "messages": [{"role": "user", "content": prompt}]}

    # try with response_format first; some providers reject it -> retry plain
    for extra in ({"response_format": {"type": "json_object"}}, None):
        p = dict(payload_base)
        if extra:
            p.update(extra)
        req = urllib.request.Request(
            base + "/chat/completions",
            data=json.dumps(p).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            print(f"[warn] HTTP {e.code} (response_format={bool(extra)}): {body}")
            if e.code not in (400, 404, 422):
                raise
            continue

        msg = data["choices"][0]["message"]
        content = (msg.get("content") or msg.get("reasoning_content") or "").strip()
        print(f"[ok] HTTP 200  response_format={'yes' if extra else 'no'}  "
              f"finish={data['choices'][0].get('finish_reason')}")
        print(f"content[:300]: {content[:300]}")
        out = extract_json(content)
        print(f"parsed: {json.dumps(out, ensure_ascii=False)[:400]}")
        results = out.get("results", [])
        assert len(results) == 2, f"expected 2 results, got {len(results)}"
        assert results[0].get("relevant") is True, results[0]
        assert results[1].get("relevant") is False, results[1]
        print("[PASS] screener round-trip: JSON structured output verified")

        if "--pipeline" in sys.argv:
            print("\n=== running full daily pipeline with LLM backend ===")
            from telescope.orchestrator import run_daily

            path = run_daily(trigger="llm-check")
            print(f"brief written: {path}\n")
            print(Path(path).read_text(encoding="utf-8")[:1500])
        return 0

    print("[FAIL] all attempts failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

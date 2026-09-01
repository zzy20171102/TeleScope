"""Diagnose summarizer LLM failures with full exception traceback."""
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telescope.agents.llm import get_backend


def main() -> int:
    backend = get_backend()
    arts = [{"id": 1, "title": "Test event headline",
             "text": "Something happened. More detail here.",
             "source_id": "s", "lang": "en", "weight": 1.0}]
    ctx = {"items_json": json.dumps(
        {"event": {"id": 1, "title": "Test", "category": "military", "severity": 1.4},
         "articles": arts}, ensure_ascii=False)}
    for i in range(3):
        try:
            out = backend.complete_json("summarizer", ctx)
            print(f"[{i}] OK: {json.dumps(out, ensure_ascii=False)[:200]}")
        except Exception:
            print(f"[{i}] FAIL:")
            traceback.print_exc()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

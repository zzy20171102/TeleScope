"""Configuration loading (sources.yaml + env settings + .env secrets)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from . import yamlmini
from .models import Source

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = Path(os.environ.get("TELESCOPE_SOURCES", ROOT / "config" / "sources.yaml"))
PROMPTS_DIR = Path(os.environ.get("TELESCOPE_PROMPTS", ROOT / "prompts"))
DB_PATH = Path(os.environ.get("TELESCOPE_DB_PATH", ROOT / "data" / "telescope.db"))
BRIEF_DIR = Path(os.environ.get("TELESCOPE_BRIEF_DIR", ROOT / "briefs"))
SNAPSHOT_DIR = Path(os.environ.get("TELESCOPE_SNAPSHOT_DIR", ROOT / "data" / "snapshots"))


def load_env_file(path: "Path | None" = None) -> dict[str, str]:
    """Load KEY=VALUE pairs from .env (never overrides existing env vars).

    The .env file is gitignored; secrets never enter the repository.
    """
    p = Path(path) if path else ROOT / ".env"
    if not p.exists():
        return {}
    loaded: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
            loaded[k] = v
    return loaded


load_env_file()  # auto-load on import; OS env vars always take precedence


def load_sources(path: "Path | None" = None, enabled_only: bool = False) -> list[Source]:
    p = path or SOURCES_PATH
    data: dict[str, Any] = yamlmini.loads(p.read_text(encoding="utf-8"))
    sources = [Source.from_dict(d) for d in data.get("sources", [])]
    if enabled_only:
        sources = [s for s in sources if s.enabled]
    return sources


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md.j2").read_text(encoding="utf-8")


_SOURCE_FIELDS = ("id", "name", "url", "type", "language", "region",
                  "perspective", "weight", "fetch_interval_minutes", "enabled")
_SPECIAL = set(":#{}[]&,*?|") | {chr(34), chr(39), chr(10), chr(13)}


def _yaml_scalar(v: Any) -> str:
    import json

    if isinstance(v, bool):
        return "true" if v else "false"
    s = str(v)
    if not s or s != s.strip() or any(ch in _SPECIAL for ch in s):
        return json.dumps(s, ensure_ascii=False)
    return s


def save_sources(sources: list[Source], path: "Path | None" = None) -> None:
    """Write sources back to YAML (single source of truth for source CRUD).

    Regenerates the file in canonical schema order; hand-written comments are
    replaced by the standard header.
    """
    p = path or SOURCES_PATH
    lines = [
        "# TeleScope 新闻源配置（单一事实来源）",
        "# 字段: id/name/url/type/language/region/perspective/weight/"
        "fetch_interval_minutes/enabled",
        "# perspective 说明: wire=通讯社 state-media=国家媒体(线索用,权重调低) "
        "多极视角显式标注",
        "",
        "sources:",
    ]
    for s in sources:
        first = True
        for k in _SOURCE_FIELDS:
            prefix = "  - " if first else "    "
            lines.append(f"{prefix}{k}: {_yaml_scalar(getattr(s, k))}")
            first = False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

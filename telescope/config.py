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

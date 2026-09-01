"""Minimal YAML-subset parser for config/sources.yaml (zero-dependency fallback).

Supports the schema we generate: nested mappings, lists of flat mappings,
scalars (str/int/float/bool), comments. Prefers PyYAML when installed.
"""
from __future__ import annotations

from typing import Any, Optional


def _scalar(s: str) -> Any:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", ""):
        return None
    for cast in (int, float):
        try:
            return cast(s)
        except ValueError:
            pass
    return s


def loads(text: str) -> dict[str, Any]:
    try:  # prefer full YAML if available
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        pass

    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    last_list: Optional[list[Any]] = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()
        container = stack[-1][1]
        if line.startswith("- "):
            body = line[2:].strip()
            if last_list is None:
                raise ValueError(f"list item outside a list: {line!r}")
            if ":" in body:
                item: dict[str, Any] = {}
                last_list.append(item)
                stack.append((indent + 2, item))
                k, _, v = body.partition(":")
                if v.strip():
                    item[k.strip()] = _scalar(v)
                else:
                    item[k.strip()] = []
                    last_list = item[k.strip()]
            else:
                last_list.append(_scalar(body))
        else:
            k, _, v = line.partition(":")
            key = k.strip()
            if v.strip():
                container[key] = _scalar(v)
            else:
                container[key] = []
                last_list = container[key]
    return root

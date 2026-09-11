"""Windows Task Scheduler integration (M1/T2.5, Factor 11 trigger).

install() writes a launcher batch file (absolute python path + project cwd,
output appended to data/daily_run.log) and registers a daily schtasks entry.
Command construction is factored out so tests can verify without touching
the real scheduler.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_TASK_NAME = "TeleScopeDaily"


def _q(p: Path | str) -> str:
    return chr(34) + str(p) + chr(34)


def bat_path(root: Path | None = None) -> Path:
    root = root or Path(__file__).resolve().parent.parent
    return root / "scripts" / "daily_task.bat"


def write_bat(root: Path, python_exe: str | None = None,
              extra_args: str = "") -> Path:
    py = python_exe or sys.executable
    root.mkdir(parents=True, exist_ok=True)
    (root / "data").mkdir(parents=True, exist_ok=True)
    ea = (extra_args.strip() + " ") if extra_args.strip() else ""
    lines = [
        "@echo off",
        "cd /d " + _q(root),
        _q(py) + " -X utf8 -m telescope run " + ea +
        ">> " + _q(root / "data" / "daily_run.log") + " 2>&1",
    ]
    p = bat_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return p


def build_create_command(task_name: str, time_: str, bat: Path) -> list[str]:
    return ["schtasks", "/Create", "/TN", task_name, "/TR", _q(bat),
            "/SC", "DAILY", "/ST", time_, "/F"]


def build_delete_command(task_name: str) -> list[str]:
    return ["schtasks", "/Delete", "/TN", task_name, "/F"]


def build_query_command(task_name: str) -> list[str]:
    return ["schtasks", "/Query", "/TN", task_name]


def _run(cmd: list[str]) -> dict[str, Any]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return {"cmd": cmd, "returncode": r.returncode,
            "stdout": (r.stdout or "").strip(),
            "stderr": (r.stderr or "").strip()}


def install(time_: str = "07:00", task_name: str = DEFAULT_TASK_NAME,
            root: Path | None = None, python_exe: str | None = None) -> dict[str, Any]:
    bat = write_bat(root or Path(__file__).resolve().parent.parent, python_exe)
    result = _run(build_create_command(task_name, time_, bat))
    result["bat"] = str(bat)
    return result


def remove(task_name: str = DEFAULT_TASK_NAME) -> dict[str, Any]:
    return _run(build_delete_command(task_name))


def show(task_name: str = DEFAULT_TASK_NAME) -> dict[str, Any]:
    return _run(build_query_command(task_name))

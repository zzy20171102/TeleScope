"""TeleScope CLI entry (Factor 11: trigger from anywhere)."""
from __future__ import annotations

import argparse
import sys

from . import config, storage
from .orchestrator import collect_all, run_daily


def cmd_run(args: argparse.Namespace) -> int:
    path = run_daily(hours=args.hours, top_n=args.top, trigger="cli")
    print(f"brief written: {path}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    from .pipeline.dedup import InBatchDeduper

    sources = config.load_sources(enabled_only=True)
    conn = storage.connect(config.DB_PATH)
    for s in sources:
        storage.upsert_source(conn, s)
    arts, errors = collect_all(sources)
    deduper = InBatchDeduper()
    n_new = 0
    for a in arts:
        if deduper.is_duplicate(a):
            continue
        if storage.upsert_article(conn, a) is not None:
            n_new += 1
    print(f"fetched={len(arts)} new={n_new} source_errors={len(errors)}")
    for e in errors:
        print(f"  [error] {e['source']}: {e['error']}", file=sys.stderr)
    conn.close()
    return 0


def cmd_sources(args: argparse.Namespace) -> int:
    for s in config.load_sources(enabled_only=args.enabled):
        print(f"{s.id:<22} {s.language:<3} {s.region:<12} "
              f"w={s.weight:<4} {s.perspective:<22} {s.name}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    conn = storage.connect(config.DB_PATH)
    for k, v in storage.stats(conn).items():
        print(f"{k:>10}: {v}")
    conn.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="telescope",
                                description="TeleScope news monitoring & brief generator")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="full daily pipeline -> brief")
    r.add_argument("--hours", type=int, default=24)
    r.add_argument("--top", type=int, default=6)
    r.set_defaults(fn=cmd_run)
    f = sub.add_parser("fetch", help="collect sources into db only")
    f.set_defaults(fn=cmd_fetch)
    s = sub.add_parser("sources", help="list configured sources")
    s.add_argument("--enabled", action="store_true")
    s.set_defaults(fn=cmd_sources)
    t = sub.add_parser("stats", help="db counters")
    t.set_defaults(fn=cmd_stats)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

"""TeleScope CLI entry (Factor 11: trigger from anywhere).

Commands: run / fetch / sources (list|add|enable|disable|check) /
stats / feedback (add|list) / schedule (install|remove|show).
"""
from __future__ import annotations

import argparse
import sys

from . import config, schedule, storage
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
        src, err = e["source"], e["error"]
        print(f"  [error] {src}: {err}", file=sys.stderr)
    conn.close()
    return 0


def cmd_sources(args: argparse.Namespace) -> int:
    for s in config.load_sources(enabled_only=getattr(args, "enabled", False)):
        mark = "" if s.enabled else " [disabled]"
        print(f"{s.id:<22} {s.language:<3} {s.region:<12} "
              f"w={s.weight:<4} {s.perspective:<22} {s.name}{mark}")
    return 0


def cmd_sources_add(args: argparse.Namespace) -> int:
    sources = config.load_sources()
    if any(s.id == args.id for s in sources):
        print(f"error: source id already exists: {args.id}", file=sys.stderr)
        return 2
    from .models import Source

    sources.append(Source(
        id=args.id, name=args.name, url=args.url, type=args.type,
        language=args.language, region=args.region,
        perspective=args.perspective, weight=args.weight,
        fetch_interval_minutes=args.fetch_interval, enabled=True))
    config.save_sources(sources)
    print(f"added {args.id} ({len(sources)} sources total) -> {config.SOURCES_PATH}")
    return 0


def _set_enabled(source_id: str, enabled: bool) -> int:
    sources = config.load_sources()
    hit = [s for s in sources if s.id == source_id]
    if not hit:
        print(f"error: unknown source id: {source_id}", file=sys.stderr)
        return 2
    hit[0].enabled = enabled
    config.save_sources(sources)
    print(f"{source_id}: enabled={enabled}")
    return 0


def cmd_sources_enable(args: argparse.Namespace) -> int:
    return _set_enabled(args.id, True)


def cmd_sources_disable(args: argparse.Namespace) -> int:
    return _set_enabled(args.id, False)


def cmd_sources_check(args: argparse.Namespace) -> int:
    from .collectors import rss

    sources = config.load_sources(enabled_only=not args.all)
    conn = storage.connect(config.DB_PATH)
    failures = 0
    try:
        for s in sources:
            storage.upsert_source(conn, s)
            try:
                recs = rss.parse_feed(rss.fetch_url(s.url, timeout=args.timeout,
                                                    retries=0))
                health = {"ok": True, "items": len(recs)}
                print(f"ok    {s.id:<22} items={len(recs)}")
            except Exception as e:  # noqa: BLE001 - report, do not crash
                failures += 1
                health = {"ok": False, "error": str(e)[:200]}
                print(f"FAIL  {s.id:<22} {str(e)[:120]}")
            storage.update_source_health(conn, s.id, health)
    finally:
        conn.close()
    print(f"checked={len(sources)} failures={failures} (health -> db)")
    return 1 if failures else 0


def cmd_stats(args: argparse.Namespace) -> int:
    conn = storage.connect(config.DB_PATH)
    for k, v in storage.stats(conn).items():
        print(f"{k:>16}: {v}")
    conn.close()
    return 0


def cmd_feedback_add(args: argparse.Namespace) -> int:
    conn = storage.connect(config.DB_PATH)
    try:
        fid = storage.save_feedback(conn, args.kind, args.target,
                                    args.rating, args.note, args.ref)
        applied = False
        if args.kind == "event_relation" and args.rating in ("confirm", "reject"):
            applied = storage.set_relation_status(
                conn, args.target,
                "confirmed" if args.rating == "confirm" else "rejected")
        print(f"feedback #{fid} saved"
              + ("; event_relations.status updated" if applied else ""))
    finally:
        conn.close()
    return 0 if (applied or args.kind != "event_relation" or
                 args.rating not in ("confirm", "reject")) else 1


def cmd_feedback_list(args: argparse.Namespace) -> int:
    conn = storage.connect(config.DB_PATH)
    try:
        rows = storage.list_feedback(conn, kind=getattr(args, "kind", None),
                                     limit=args.limit)
        for r in rows:
            rid, created = r["id"], r["created_at"]
            kind, target, rating = r["kind"], r["target_id"], r["rating"]
            ref, note = r["ref"], r["note"]
            line = f"#{rid} {created} {kind:<14} target={target} rating={rating}"
            if ref:
                line += f" ref={ref}"
            if note:
                line += f" note={note}"
            print(line)
        print(f"total={len(rows)}")
    finally:
        conn.close()
    return 0


def cmd_schedule_install(args: argparse.Namespace) -> int:
    result = schedule.install(time_=args.time, task_name=args.task_name)
    ok = result["returncode"] == 0
    bat = result["bat"]
    print(("installed" if ok else "FAILED") +
          f" task={args.task_name} time={args.time} bat={bat}")
    if result["stdout"]:
        print(result["stdout"])
    if result["stderr"]:
        print(result["stderr"], file=sys.stderr)
    return 0 if ok else 1


def cmd_schedule_remove(args: argparse.Namespace) -> int:
    result = schedule.remove(args.task_name)
    ok = result["returncode"] == 0
    print("removed" if ok else "FAILED (not installed?)")
    if result["stderr"]:
        print(result["stderr"], file=sys.stderr)
    return 0 if ok else 1


def cmd_schedule_show(args: argparse.Namespace) -> int:
    result = schedule.show(args.task_name)
    if result["returncode"] == 0 and result["stdout"]:
        print(result["stdout"])
        return 0
    print(f"task {args.task_name} not found", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="telescope",
        description="TeleScope news monitoring & brief generator")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="full daily pipeline -> brief")
    r.add_argument("--hours", type=int, default=24)
    r.add_argument("--top", type=int, default=6)
    r.set_defaults(fn=cmd_run)

    f = sub.add_parser("fetch", help="collect sources into db only")
    f.set_defaults(fn=cmd_fetch)

    s = sub.add_parser("sources", help="manage news sources")
    s.set_defaults(fn=cmd_sources)
    s_sub = s.add_subparsers(dest="sources_cmd")
    sl = s_sub.add_parser("list", help="list configured sources")
    sl.add_argument("--enabled", action="store_true")
    sl.set_defaults(fn=cmd_sources)
    sa = s_sub.add_parser("add", help="add a source to sources.yaml")
    sa.add_argument("--id", required=True)
    sa.add_argument("--name", required=True)
    sa.add_argument("--url", required=True)
    sa.add_argument("--type", default="rss")
    sa.add_argument("--language", default="en")
    sa.add_argument("--region", default="global")
    sa.add_argument("--perspective", default="unlabeled")
    sa.add_argument("--weight", type=float, default=1.0)
    sa.add_argument("--fetch-interval", type=int, default=60,
                    dest="fetch_interval")
    sa.set_defaults(fn=cmd_sources_add)
    se = s_sub.add_parser("enable", help="enable a source by id")
    se.add_argument("id")
    se.set_defaults(fn=cmd_sources_enable)
    sd = s_sub.add_parser("disable", help="disable a source by id")
    sd.add_argument("id")
    sd.set_defaults(fn=cmd_sources_disable)
    sc = s_sub.add_parser("check", help="fetch every source and record health")
    sc.add_argument("--all", action="store_true",
                    help="include disabled sources")
    sc.add_argument("--timeout", type=int, default=20)
    sc.set_defaults(fn=cmd_sources_check)

    t = sub.add_parser("stats", help="db counters")
    t.set_defaults(fn=cmd_stats)

    fb = sub.add_parser("feedback", help="human feedback loop (Factor 7)")
    fb.set_defaults(fn=cmd_feedback_list)
    fb_sub = fb.add_subparsers(dest="feedback_cmd")
    fa = fb_sub.add_parser("add", help="record feedback for a target")
    fa.add_argument("--kind", required=True,
                    choices=["brief_item", "event_relation", "source"])
    fa.add_argument("--target", type=int, required=True)
    fa.add_argument("--rating", required=True,
                    choices=["good", "bad", "confirm", "reject"])
    fa.add_argument("--ref", default="", help="e.g. brief item number")
    fa.add_argument("--note", default="")
    fa.set_defaults(fn=cmd_feedback_add)
    fl = fb_sub.add_parser("list", help="recent feedback rows")
    fl.add_argument("--kind", default=None)
    fl.add_argument("--limit", type=int, default=20)
    fl.set_defaults(fn=cmd_feedback_list)

    sch = sub.add_parser("schedule", help="Windows daily task (07:00 default)")
    sch.set_defaults(fn=cmd_schedule_show)
    sch_sub = sch.add_subparsers(dest="schedule_cmd")
    si = sch_sub.add_parser("install", help="register daily scheduled task")
    si.add_argument("--time", default="07:00")
    si.add_argument("--task-name", default=schedule.DEFAULT_TASK_NAME)
    si.set_defaults(fn=cmd_schedule_install)
    sr = sch_sub.add_parser("remove", help="delete the scheduled task")
    sr.add_argument("--task-name", default=schedule.DEFAULT_TASK_NAME)
    sr.set_defaults(fn=cmd_schedule_remove)
    ss = sch_sub.add_parser("show", help="query the scheduled task")
    ss.add_argument("--task-name", default=schedule.DEFAULT_TASK_NAME)
    ss.set_defaults(fn=cmd_schedule_show)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

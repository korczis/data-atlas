"""`atlas-data` — the command line for the warehouse subsystem.

Grouped by the stage of the pipeline each command belongs to:

    source   discover · fetch · verify · inventory · status
    db       migrate · status · reset
    ingest   stage · load
    mart     build · analyze
    quality  run
    report   coverage · fields · storage · reconcile
    docs     generate

Every command exits non-zero when it fails, prints human-readable progress to
stderr and machine-readable JSON to stdout under `--json`, and refuses to
report success for work it did not do.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from . import config
from .logging import configure, emit, log


def _add_selection(p: argparse.ArgumentParser) -> None:
    """Artifact selection, shared by every command that walks a manifest."""
    p.add_argument("--dataset", default="cia_world_factbook",
                   help="dataset code (default: %(default)s)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="every artifact in the manifest")
    g.add_argument("--year", type=int, action="append", dest="years",
                   help="one edition year; repeatable")
    g.add_argument("--artifact", action="append", dest="artifact_ids",
                   help="one artifact id; repeatable")
    p.add_argument("--from", dest="year_from", type=int, help="first edition year")
    p.add_argument("--to", dest="year_to", type=int, help="last edition year")
    p.add_argument("--family", action="append", dest="families",
                   help="parser family, e.g. json_factbook_cache; repeatable")


def _selected(args: argparse.Namespace):
    from . import manifest as manifest_mod

    m = manifest_mod.load(args.dataset)
    years: set[int] | None = None
    if args.years:
        years = set(args.years)
    if args.year_from is not None or args.year_to is not None:
        lo = args.year_from if args.year_from is not None else min(m.years)
        hi = args.year_to if args.year_to is not None else max(m.years)
        years = (years or set()) | set(range(lo, hi + 1)) if args.years else set(range(lo, hi + 1))

    ids = set(args.artifact_ids) if args.artifact_ids else None
    fams = set(args.families) if args.families else None

    if years is None and ids is None and fams is None and not args.all:
        raise SystemExit(
            "refusing to act on an unspecified selection — pass --all, --year, "
            "--from/--to, --family or --artifact.\n"
            "A command that silently defaults to 'everything' is how 3 GB gets "
            "downloaded by accident; one that defaults to 'nothing' reports "
            "success having done no work.")
    return m, m.select(years=years, families=fams, artifact_ids=ids)


# ── source ────────────────────────────────────────────────────────────────────

def cmd_source_discover(args: argparse.Namespace) -> int:
    """What the manifest claims exists. Offline: this reads curated data."""
    from . import manifest as manifest_mod

    m = manifest_mod.load(args.dataset)
    log("info", f"{m.dataset.title} — {m.dataset.code}")
    log("info", f"publisher: {m.dataset.publisher['name']} · status: {m.dataset.status}")
    print(f"{'year':<6}{'artifact_id':<26}{'family':<22}{'role':<12}{'size':>14}  file")
    for a in sorted(m.artifacts, key=lambda x: (x.edition_year, x.artifact_id)):
        print(f"{a.edition_year:<6}{a.artifact_id:<26}{a.parser_family:<22}"
              f"{a.role:<12}{a.size_bytes:>14,}  {a.filename}")
        emit({"artifact_id": a.artifact_id, "year": a.edition_year,
              "family": a.parser_family, "role": a.role, "sha256": a.sha256,
              "size_bytes": a.size_bytes})
    total = sum(a.size_bytes for a in m.artifacts)
    log("info", f"{len(m.artifacts)} artifacts across {len(m.years)} editions, "
                f"{total:,} bytes ({total / 1024**3:.2f} GiB)")
    return 0


def cmd_source_fetch(args: argparse.Namespace) -> int:
    import shutil

    from .fetch import DigestMismatch, FetchError, fetch_artifact

    _manifest, selected = _selected(args)
    if not selected:
        log("error", "selection matched no artifacts")
        return 1

    want = [a for a in selected if not a.path().exists()]
    need_bytes = sum(a.size_bytes for a in want)
    free = shutil.disk_usage(config.RAW.parent).free
    log("info", f"selected {len(selected)} artifacts; {len(want)} not yet on disk")
    log("info", f"to download {need_bytes:,} bytes ({need_bytes / 1024**3:.2f} GiB); "
                f"free {free:,} ({free / 1024**3:.1f} GiB)")

    # Refuse rather than fill the disk. Extraction and PostgreSQL both need room
    # beyond the download itself, so the margin is deliberate.
    if need_bytes * 3 > free:
        log("error", "not enough free space for the download plus extraction "
                     "headroom (3x compressed size). Narrow the selection.")
        return 1
    if args.dry_run:
        for a in want:
            log("info", f"would fetch {a.artifact_id}", url=a.best_retrieval().url)
        return 0

    ok = failed = present = 0
    downloaded_bytes = 0
    for a in sorted(selected, key=lambda x: (x.edition_year, x.artifact_id)):
        try:
            r = fetch_artifact(a, timeout=args.timeout)
        except DigestMismatch as exc:
            log("error", str(exc))
            failed += 1
            continue
        except FetchError as exc:
            log("error", f"{a.artifact_id}: {exc}")
            failed += 1
            continue
        if r.status == "present":
            present += 1
        else:
            ok += 1
            downloaded_bytes += r.bytes_downloaded
            log("info", f"fetched {a.artifact_id}", bytes=f"{r.bytes_downloaded:,}")
        emit({"artifact_id": a.artifact_id, "status": r.status,
              "bytes_downloaded": r.bytes_downloaded, "path": str(r.path)})

    log("info", f"downloaded {ok}, already present {present}, failed {failed}; "
                f"{downloaded_bytes:,} bytes transferred")
    return 1 if failed else 0


def cmd_source_verify(args: argparse.Namespace) -> int:
    """Re-hash every selected artifact. The check that actually means something."""
    from .fetch import verify_artifact

    _manifest, selected = _selected(args)
    if not selected:
        log("error", "selection matched no artifacts")
        return 1

    good = bad = missing = 0
    for a in sorted(selected, key=lambda x: (x.edition_year, x.artifact_id)):
        ok, reason = verify_artifact(a)
        if ok:
            good += 1
            log("debug", f"{a.artifact_id}: ok")
        elif reason == "absent":
            missing += 1
            log("warn", f"{a.artifact_id}: not downloaded")
        else:
            bad += 1
            log("error", f"{a.artifact_id}: {reason}")
        emit({"artifact_id": a.artifact_id, "verified": ok, "reason": reason})

    log("info", f"verified {good} ok, {bad} corrupt, {missing} absent "
                f"(of {len(selected)} selected)")
    # Absent is not corrupt: it means "not fetched yet", which is a normal state
    # and must not read as a verification failure.
    return 1 if bad else 0


def cmd_source_inventory(args: argparse.Namespace) -> int:
    """What is actually on disk, independent of what the manifest expects."""
    from . import manifest as manifest_mod

    m = manifest_mod.load(args.dataset)
    known = {a.sha256: a for a in m.artifacts}
    if not config.RAW.exists():
        log("warn", f"{config.RAW} does not exist — nothing fetched yet")
        return 0

    total = 0
    rows = []
    for digest_dir in sorted(config.RAW.iterdir()):
        if not digest_dir.is_dir():
            continue
        for f in sorted(digest_dir.iterdir()):
            if f.name.endswith((".partial", )) or ".rejected-" in f.name:
                rows.append((digest_dir.name, f.name, f.stat().st_size, "INCOMPLETE"))
                continue
            size = f.stat().st_size
            total += size
            a = known.get(digest_dir.name)
            rows.append((digest_dir.name, f.name, size,
                         a.artifact_id if a else "UNKNOWN-to-manifest"))

    print(f"{'sha256':<18}{'size':>14}  {'artifact':<26} file")
    for digest, name, size, label in rows:
        print(f"{digest[:16]:<18}{size:>14,}  {label:<26} {name}")
        emit({"sha256": digest, "file": name, "size_bytes": size, "artifact": label})
    log("info", f"{len(rows)} files on disk, {total:,} bytes ({total / 1024**3:.2f} GiB) "
                f"under {config.RAW}")
    return 0


def cmd_source_status(args: argparse.Namespace) -> int:
    """Manifest versus disk, per edition. Cheap: sizes, not hashes."""
    from . import manifest as manifest_mod

    m = manifest_mod.load(args.dataset)
    on_disk = have_bytes = 0
    per_family: dict[str, list[int]] = {}
    for a in m.artifacts:
        present = a.path().exists() and a.path().stat().st_size == a.size_bytes
        on_disk += present
        have_bytes += a.size_bytes if present else 0
        per_family.setdefault(a.parser_family, [0, 0])
        per_family[a.parser_family][1] += 1
        per_family[a.parser_family][0] += present

    print(f"{'parser family':<24}{'on disk':>10}{'total':>8}")
    for fam, (have, tot) in sorted(per_family.items()):
        print(f"{fam:<24}{have:>10}{tot:>8}")
    total_bytes = sum(a.size_bytes for a in m.artifacts)
    print()
    print(f"artifacts on disk : {on_disk}/{len(m.artifacts)}")
    print(f"bytes on disk     : {have_bytes:,} of {total_bytes:,} "
          f"({100 * have_bytes / total_bytes:.1f}%)")
    emit({"artifacts_present": on_disk, "artifacts_total": len(m.artifacts),
          "bytes_present": have_bytes, "bytes_total": total_bytes})
    return 0


# ── dispatch ──────────────────────────────────────────────────────────────────

def _lazy(module: str, func: str) -> Callable[[argparse.Namespace], int]:
    """Import command implementations only when called.

    `atlas-data source status` must work with no database driver installed, so
    nothing that touches psycopg may be imported at module load.
    """
    def run(args: argparse.Namespace) -> int:
        import importlib
        mod = importlib.import_module(f".{module}", package="atlasdata")
        return getattr(mod, func)(args)
    return run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="atlas-data",
        description="Ingestion and warehouse tooling for the Data Atlas data platform.")
    p.add_argument("--verbose", "-v", action="store_true", help="debug-level logging")
    p.add_argument("--quiet", "-q", action="store_true", help="errors only")
    p.add_argument("--json", action="store_true",
                   help="machine-readable results on stdout")
    sub = p.add_subparsers(dest="group", required=True)

    # source
    s = sub.add_parser("source", help="acquire and verify raw artifacts").add_subparsers(
        dest="command", required=True)

    d = s.add_parser("discover", help="what the manifest says exists")
    d.add_argument("--dataset", default="cia_world_factbook")
    d.set_defaults(func=cmd_source_discover)

    f = s.add_parser("fetch", help="download artifacts and verify their digests")
    _add_selection(f)
    f.add_argument("--timeout", type=float, default=60.0)
    f.add_argument("--dry-run", action="store_true",
                   help="say what would be fetched, transfer nothing")
    f.set_defaults(func=cmd_source_fetch)

    v = s.add_parser("verify", help="re-hash what is on disk")
    _add_selection(v)
    v.set_defaults(func=cmd_source_verify)

    i = s.add_parser("inventory", help="what is on disk, manifest or not")
    i.add_argument("--dataset", default="cia_world_factbook")
    i.set_defaults(func=cmd_source_inventory)

    st = s.add_parser("status", help="manifest versus disk, by parser family")
    st.add_argument("--dataset", default="cia_world_factbook")
    st.set_defaults(func=cmd_source_status)

    # db
    db = sub.add_parser("db", help="schema lifecycle").add_subparsers(
        dest="command", required=True)
    mig = db.add_parser("migrate", help="apply pending migrations")
    mig.add_argument("--dry-run", action="store_true")
    mig.set_defaults(func=_lazy("migrate", "cmd_migrate"))
    dbs = db.add_parser("status", help="applied migrations and extension state")
    dbs.set_defaults(func=_lazy("migrate", "cmd_status"))
    dbr = db.add_parser("reset", help="DROP and recreate every managed schema")
    dbr.add_argument("--yes", action="store_true", help="required; this destroys data")
    dbr.set_defaults(func=_lazy("migrate", "cmd_reset"))

    # ingest
    ing = sub.add_parser("ingest", help="parse and load a dataset").add_subparsers(
        dest="command", required=True)
    stg = ing.add_parser("stage", help="artifacts -> staging tables, losslessly")
    _add_selection(stg)
    stg.add_argument("--limit-entities", type=int,
                     help="stop after N entities per artifact (development aid)")
    stg.set_defaults(func=_lazy("staging", "cmd_stage"))
    ld = ing.add_parser("load", help="staging -> canonical typed observations")
    ld.add_argument("--dataset", default="cia_world_factbook")
    ld.add_argument("--bootstrap-entities", action="store_true",
                    help="create an 'unclassified' entity for each unresolved source "
                         "entry, asserting only that the entry exists. Explicit "
                         "because it writes to the entity registry; see "
                         "docs/database/ENTITY-IDENTITY.md")
    ld.set_defaults(func=_lazy("loader", "cmd_load"))

    # mart
    mt = sub.add_parser("mart", help="dimensional projection").add_subparsers(
        dest="command", required=True)
    mb = mt.add_parser("build", help="refresh every materialised view in mart")
    mb.add_argument("--concurrently", action="store_true",
                    help="REFRESH ... CONCURRENTLY; requires the views to be populated "
                         "already and cannot run on a first build")
    mb.set_defaults(func=_lazy("mart", "cmd_build"))
    ma = mt.add_parser("analyze", help="ANALYZE so the planner has real statistics")
    ma.set_defaults(func=_lazy("mart", "cmd_analyze"))

    # quality
    q = sub.add_parser("quality", help="run the data-quality suite").add_subparsers(
        dest="command", required=True)
    qr = q.add_parser("run", help="execute every implemented check and record findings")
    qr.add_argument("--dataset", default="cia_world_factbook")
    qr.add_argument("--deep", action="store_true",
                    help="re-hash every artifact rather than only checking size "
                         "and presence; slow (2.8 GB) but the only real digest check")
    qr.set_defaults(func=_lazy("quality", "cmd_quality"))

    # report
    rep = sub.add_parser("report", help="what actually landed").add_subparsers(
        dest="command", required=True)
    for name, helptext in [("coverage", "editions, entities, fields per year"),
                           ("fields", "raw field evolution across editions"),
                           ("storage", "table, index and toast sizes"),
                           ("reconcile", "expected versus parsed versus loaded")]:
        r = rep.add_parser(name, help=helptext)
        r.add_argument("--dataset", default="cia_world_factbook")
        r.set_defaults(func=_lazy("reports", f"cmd_{name}"))

    # docs
    doc = sub.add_parser("docs", help="generate documentation from the live schema"
                         ).add_subparsers(dest="command", required=True)
    dg = doc.add_parser("generate", help="schema reference and ERDs")
    dg.set_defaults(func=_lazy("docsgen", "cmd_generate"))

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    level = "debug" if args.verbose else "error" if args.quiet else "info"
    configure(level=level, json_output=args.json)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        log("error", "interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())

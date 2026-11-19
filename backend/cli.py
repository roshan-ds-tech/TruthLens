"""TruthLens command line: analyze files, rerun a case, run validation, export a report.

    truthlens analyze clip.mp4 photo.jpg --caption "…12 Nov 2026" [--title T] [--report]
    truthlens rerun --case C-0007
    truthlens report --case C-0007
    truthlens validate
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import config, custody, db, pipeline, registry  # noqa: E402
from app.api import adapters  # noqa: E402
from app.ingest.service import IngestError, ingest_file, ingest_text  # noqa: E402
from app.models import Case  # noqa: E402


def _print_case(s, case: Case) -> dict:
    d = adapters.case_detail(s, case)
    v = d["verdict"]
    rng = f" {v['lo']:.2f}–{v['hi']:.2f}" if v.get("lo") is not None else ""
    print(f"\n{d['id']} · {d['title']}\nVerdict: {v['label']}{rng}\nWhy: {v['why']}\n")
    for f in adapters.case_findings(s, case.id):
        print(f"  {f['finding_id']:10s} {f['verdict']['label']:28s} {f['conf_low']:.2f}–{f['conf_high']:.2f}  {f['name']} · {f['loc_label']}")
    lim = d["limitations"][len(config.GENERAL_LIMITATIONS):]
    if lim:
        print("\nLimitations for this run:")
        for line in lim:
            print("  -", line)
    return d


def cmd_analyze(args) -> int:
    from app.api.routes import next_case_id

    with db.session() as s:
        case = Case(id=next_case_id(s), title=args.title or ", ".join(Path(f).name for f in args.files[:2]),
                    investigator=args.investigator or registry.investigator(s), description=args.description or "")
        s.add(case)
        s.commit()
        custody.log(s, case.id, case.investigator, "Case opened", f"truthlens-cli {config.APP_VERSION}", "—",
                    f"case {custody.sha256_json([case.id, case.title])}")
        for f in args.files:
            try:
                ev = ingest_file(s, case, Path(f), Path(f).name, case.investigator)
                print(f"{ev.label}  {ev.kind:5s}  sha256 {ev.sha256}  {Path(f).name}")
            except IngestError as exc:
                print(f"rejected {f}: {exc}", file=sys.stderr)
        if args.caption:
            text = Path(args.caption).read_text("utf-8") if Path(args.caption).is_file() else args.caption
            ev = ingest_text(s, case, text, case.investigator)
            print(f"{ev.label}  text   sha256 {ev.sha256}  caption")
        print(f"\nAnalyzing {case.id}…")
        pipeline.run_case(s, case.id, None, case.investigator)
        s.refresh(case)
        d = _print_case(s, case)
        if args.report:
            from app.report import render

            r = render.build(s, case)
            print(f"\nReport sha256 {r['sha256']}\n  {config.REPORT_DIR / case.id / ('draft' + str(r['draft']))}")
        if args.json:
            print(json.dumps(adapters.case_findings(s, case.id), indent=2, default=str))
    return 0


def cmd_rerun(args) -> int:
    with db.session() as s:
        case = s.get(Case, args.case)
        if case is None:
            print(f"case {args.case} not found", file=sys.stderr)
            return 1
        before = [e for e in custody.entries(s, case.id) if e.action.startswith("Analysis run")]
        out = pipeline.run_case(s, case.id, None, "truthlens-cli")
        s.refresh(case)
        _print_case(s, case)
        if before:
            same = before[-1].output_hash == f"findings {out['digest']}"
            print(f"\nRerun reproduces previous run: {'yes' if same else 'NO'} (findings {custody.short(out['digest'])})")
            return 0 if same else 2
    return 0


def cmd_report(args) -> int:
    from app.report import render

    with db.session() as s:
        case = s.get(Case, args.case)
        if case is None:
            print(f"case {args.case} not found", file=sys.stderr)
            return 1
        r = render.build(s, case)
        print(json.dumps(r, indent=2))
    return 0


def cmd_validate(args) -> int:
    script = config.VALIDATION_DIR / "run_validation.py"
    return subprocess.call([sys.executable, str(script)] + (["--quick"] if args.quick else []))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="truthlens", description="Offline multimodal forensic triage")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="open a case from files and analyze it")
    a.add_argument("files", nargs="*")
    a.add_argument("--caption", help="caption text, or a path to a .txt file")
    a.add_argument("--title")
    a.add_argument("--description")
    a.add_argument("--investigator")
    a.add_argument("--report", action="store_true", help="also export the PDF/JSON report")
    a.add_argument("--json", action="store_true", help="print findings as JSON")
    a.set_defaults(fn=cmd_analyze)
    r = sub.add_parser("rerun", help="re-analyze a case from its stored originals")
    r.add_argument("--case", required=True)
    r.set_defaults(fn=cmd_rerun)
    rp = sub.add_parser("report", help="export the report for a case")
    rp.add_argument("--case", required=True)
    rp.set_defaults(fn=cmd_report)
    v = sub.add_parser("validate", help="build the seeded test set and compute metrics")
    v.add_argument("--quick", action="store_true")
    v.set_defaults(fn=cmd_validate)
    args = p.parse_args(argv)
    if args.cmd == "analyze" and not args.files and not args.caption:
        p.error("give at least one file or --caption")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

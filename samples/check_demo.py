"""Analyze samples/demo_case in a fresh data folder and compare with samples/expected_report.json.

    python samples/check_demo.py            # compare (exit 1 on any difference)
    python samples/check_demo.py --update   # write expected_report.json from this run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")

DEMO = ROOT / "samples" / "demo_case"
EXPECTED = ROOT / "samples" / "expected_report.json"


def run() -> dict:
    from app import config, db, pipeline
    from app.api import adapters
    from app.api.routes import graph_for
    from app.ingest.service import ingest_file, ingest_text
    from app.models import Case
    from app.report import render

    config.set_data_dir(tempfile.mkdtemp(prefix="tl-demo-"))
    db.reset_engine()
    with db.session() as s:
        case = Case(id="C-0007", title="Viral clip: minister announces holiday", investigator="Priya S.",
                    description="Clip and podium photo forwarded on WhatsApp on 12 Nov 2026.")
        s.add(case)
        s.commit()
        ingest_file(s, case, DEMO / "clip.mp4", "minister_holiday_clip.mp4", "Priya S.")
        ingest_file(s, case, DEMO / "podium_photo.jpg", "podium_photo.jpg", "Priya S.")
        ingest_text(s, case, (DEMO / "caption.txt").read_text("utf-8"), "Priya S.", "WhatsApp forward")
        out = pipeline.run_case(s, case.id, None, "Priya S.")
        s.refresh(case)
        detail = adapters.case_detail(s, case)
        report = render.build(s, case)
        findings = adapters.case_findings(s, case.id)
        rules = graph_for(s, case)["rules"]
    return {
        "case": case.id,
        "findings_digest": out["digest"],
        "verdict": {k: detail["verdict"][k] for k in ("band", "lo", "hi")},
        "deepfake": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in (detail.get("deepfake") or {}).items()
                     if k in ("key", "p", "lo", "hi", "driver")},
        # Originals must hash identically everywhere. A derived track's bytes depend on the local ffmpeg build
        # (AAC decoders differ between versions), so only its kind and verdict are compared.
        "evidence": {e["label"]: {"kind": e["kind"], "band": e["verdict"]["band"],
                                  "deepfake": (e.get("deepfake") or {}).get("key"),
                                  **({} if e.get("derived_from") else {"sha256": e["sha256"]})} for e in detail["evidence"]},
        "findings": [{k: f[k] for k in ("finding_id", "evidence_id", "indicator", "loc_label", "conf_low", "conf_high", "band")}
                     for f in findings],
        "rules": sorted({r["id"] for r in rules}),
        "report_pdf": bool(report["files"]["pdf"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true")
    args = ap.parse_args()
    got = run()
    print(f"{got['case']} · {got['verdict']['band']} {got['verdict']['lo']:.2f}–{got['verdict']['hi']:.2f} · rules {', '.join(got['rules'])}")
    for f in got["findings"]:
        print(f"  {f['finding_id']:10s} {f['band']:13s} {f['conf_low']:.2f}–{f['conf_high']:.2f}  {f['indicator']} · {f['loc_label']}")
    if args.update or not EXPECTED.exists():
        EXPECTED.write_text(json.dumps(got, indent=2))
        print(f"\nwrote {EXPECTED}")
        return 0
    want = json.loads(EXPECTED.read_text())
    if want == got:
        print("\nDemo reproduces samples/expected_report.json exactly.")
        return 0
    for key in want:
        if want[key] != got.get(key):
            print(f"\nDIFFERENT {key}:\n  expected {json.dumps(want[key])[:400]}\n  got      {json.dumps(got.get(key))[:400]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

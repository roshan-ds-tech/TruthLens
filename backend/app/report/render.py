"""Report: HTML (Jinja2) → PDF (WeasyPrint) plus report.json (§3.9).

The report hash is the SHA-256 of the canonical report.json content (without the hash field). It is
printed in the PDF footer and logged in custody, together with the PDF file's own hash.
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageDraw, ImageOps
from sqlmodel import Session, select

from .. import config, custody
from ..api import adapters
from ..models import Case, Evidence, JsonMixin, ReportRow, utcnow

TEMPLATES = Path(__file__).parent / "templates"


def _png_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _thumb(f: dict, ev: Evidence) -> Optional[str]:
    """Evidence crop for a finding: region box for images/frames, spectrogram slice for audio."""
    loc = f["location"]
    try:
        if loc.get("type") in ("bbox",) or (loc.get("type") == "frame_range" and loc.get("w")):
            if ev.kind == "image":
                with Image.open(custody.original_path(ev.case_id, ev.sha256)) as im:
                    src = ImageOps.exif_transpose(im).convert("RGB")
            else:
                import cv2

                cap = cv2.VideoCapture(str(custody.original_path(ev.case_id, ev.sha256)))
                cap.set(cv2.CAP_PROP_POS_MSEC, float(loc.get("start", 0)) * 1000)
                ok, frame = cap.read()
                cap.release()
                if not ok:
                    return None
                src = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            sx, sy = src.width / (loc.get("image_w") or src.width), src.height / (loc.get("image_h") or src.height)
            x, y, w, h = loc["x"] * sx, loc["y"] * sy, loc["w"] * sx, loc["h"] * sy
            pad = max(w, h) * 0.35
            box = (max(0, x - pad), max(0, y - pad), min(src.width, x + w + pad), min(src.height, y + h + pad))
            crop = src.crop(tuple(int(v) for v in box))
            d = ImageDraw.Draw(crop)
            d.rectangle([x - box[0], y - box[1], x - box[0] + w, y - box[1] + h], outline=(255, 210, 63), width=3)
            crop.thumbnail((240, 150))
            return _png_uri(crop)
        if loc.get("type") == "frame_range" and ev.kind == "video":
            import cv2

            cap = cv2.VideoCapture(str(custody.original_path(ev.case_id, ev.sha256)))
            cap.set(cv2.CAP_PROP_POS_MSEC, float(loc.get("start", 0)) * 1000)
            ok, frame = cap.read()
            cap.release()
            if ok:
                im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                im.thumbnail((240, 150))
                return _png_uri(im)
        if loc.get("type") == "time_range" and ev.kind == "audio":
            spec = config.ARTIFACT_DIR / ev.case_id / ev.label / "spectrogram.png"
            dur = JsonMixin.loads(ev.metadata_json, {}).get("duration") or 1
            if spec.exists():
                with Image.open(spec) as im:
                    a = max(0.0, (loc["start"] - 1.5) / dur) * im.width
                    b = min(1.0, (loc["end"] + 1.5) / dur) * im.width
                    crop = im.convert("RGB").crop((int(a), 0, max(int(b), int(a) + 10), im.height))
                    d = ImageDraw.Draw(crop)
                    xa, xb = loc["start"] / dur * im.width - a, loc["end"] / dur * im.width - a
                    d.rectangle([xa, 0, xb, im.height - 1], outline=(224, 180, 0), width=2)
                    crop.thumbnail((240, 150))
                    return _png_uri(crop)
    except Exception:
        return None
    return None


def _summary(case: dict, findings: list[dict]) -> str:
    kinds = [e["kind"] for e in case["evidence"]]
    parts = ", ".join(f"{kinds.count(k)} {k}" for k in ("video", "audio", "image", "text") if k in kinds)
    acc = sum(f["review"]["status"] == "accepted" for f in findings)
    rej = sum(f["review"]["status"] == "rejected" for f in findings)
    open_ = len(findings) - acc - rej
    desc = case["description"].strip()
    lead = (desc + ("" if desc.endswith((".", "!", "?")) else ".") + " ") if desc else ""
    return (f"{lead}{len(kinds)} evidence item{'s' if len(kinds) != 1 else ''} ({parts}) were analyzed on this device. "
            f"{len(findings)} finding{'s were' if len(findings) != 1 else ' was'} produced; {acc} accepted by the reviewer, "
            f"{rej} rejected and {open_} still open.")


def _checks(findings: list[dict]) -> list[str]:
    out = []
    for f in sorted(findings, key=lambda f: -f["score"])[:4]:
        if f["review"]["status"] == "rejected" or not f["alternatives"]:
            continue
        out.append(f"{f['finding_id']}: rule out \"{f['alternatives'][0]}\" before relying on it.")
    if not out:
        out.append("No finding needs follow-up; keep the originals and this report together.")
    return out


def build(s: Session, case_row: Case) -> dict[str, Any]:
    from ..api.routes import case_custody, case_graph

    case = adapters.case_detail(s, case_row)
    findings = adapters.case_findings(s, case_row.id)
    graph = case_graph(case_row.id, s)
    evs = {e.id: e for e in s.exec(select(Evidence).where(Evidence.case_id == case_row.id))}
    custody_info = case_custody(case_row.id, s)
    draft = len(s.exec(select(ReportRow).where(ReportRow.case_id == case_row.id)).all()) + 1
    claims = []
    for e in case["evidence"]:
        if e["kind"] == "text":
            for c in JsonMixin.loads(evs[e["id"]].extra_json, {}).get("claims", []):
                claims.append({"evidence": e["label"], **c})
    ev_shas = [evs[e["id"]].sha256 for e in case["evidence"] if not e.get("derived_from")]
    report: dict[str, Any] = {
        "schema": "truthlens.report/1",
        "case": {"id": case["id"], "title": case["title"], "investigator": case["investigator"],
                 "description": case["description"], "opened": case["created_at"]},
        "generated_at": utcnow().isoformat(), "draft": draft, "app_version": config.APP_VERSION,
        "summary": _summary(case, findings),
        "verdict": case["verdict"],
        "evidence": [{"label": e["label"], "name": e["display_name"], "type": e["kind"].capitalize(), "size": e["size"],
                      "meta": e["meta_label"], "sha256": e["sha256"], "derived_from": e.get("derived_from"),
                      "verdict": e["verdict"]} for e in case["evidence"]],
        "findings": [{k: f[k] for k in ("finding_id", "evidence_id", "modality", "indicator", "name", "location", "loc_label",
                                        "score", "conf_low", "conf_high", "band", "verdict", "method", "explanation",
                                        "alternatives", "calibrated", "weakened", "review")} for f in findings],
        "claims": claims,
        "correlations": graph["rules"], "graph": {"nodes": graph["nodes"], "edges": graph["edges"]},
        "limitations": case["limitations"],
        "recommended_checks": _checks(findings),
        "review_decisions": [{"finding_id": f["finding_id"], "decision": f["review"]["status"],
                              "time": f["review"]["decided_at"], "reviewer": f["review"]["reviewer"],
                              "note": f["review"]["note"]} for f in findings],
        "rerun_command": f"truthlens rerun --case {case['id']}",
        "rerun_detail": f"truthlens analyze --case {case['id']} --seed {config.SEED} --evidence "
                        + " ".join(custody.short(h) for h in ev_shas),
        "custody": {"entries": len(custody_info["entries"]) + 1, "chain_valid": custody_info["chain_valid"]},
    }
    report_sha = custody.sha256_json(report)
    report["sha256"] = report_sha

    out_dir = config.REPORT_DIR / case_row.id / f"draft{draft}"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "report.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    thumbs = {f["finding_id"]: _thumb(f, evs[f["evidence_db_id"]]) for f in findings}
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]))
    html = env.get_template("report.html.j2").render(r=report, thumbs=thumbs, short=custody.short)
    html_path = out_dir / "report.html"
    html_path.write_text(html, "utf-8")

    pdf_path: Optional[Path] = out_dir / "report.pdf"
    pdf_error = None
    try:
        from weasyprint import HTML

        HTML(string=html, base_url=str(out_dir)).write_pdf(str(pdf_path))
    except Exception as exc:  # WeasyPrint needs pango; the HTML and JSON are still complete without it
        pdf_path, pdf_error = None, f"{exc.__class__.__name__}: {str(exc)[:160]}"
    pdf_sha = custody.sha256_file(pdf_path) if pdf_path else None
    s.add(ReportRow(case_id=case_row.id, path_pdf=str(pdf_path) if pdf_path else None, path_json=str(json_path),
                    path_html=str(html_path), sha256=report_sha))
    s.commit()
    custody.log(s, case_row.id, case_row.investigator, f"Report draft {draft} generated", f"tl-report {config.APP_VERSION}",
                f"review {custody.sha256_json(report['review_decisions'])}",
                f"sha256 {report_sha}" + (f" · pdf {pdf_sha}" if pdf_sha else ""))
    return {"sha256": report_sha, "draft": draft, "pdf_sha256": pdf_sha, "pdf_error": pdf_error,
            "files": {"pdf": f"/api/cases/{case_row.id}/report.pdf" if pdf_path else None,
                      "json": f"/api/cases/{case_row.id}/report.json", "html": f"/api/cases/{case_row.id}/report.html"}}

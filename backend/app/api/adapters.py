"""Response shapes the existing UI expects (see docs/ui_integration_map.md).

The UI already uses short verdict keys (strong / ind / inc / none / review) and specific field
names; these adapters translate database rows into exactly that vocabulary.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session, select

from .. import config, custody
from ..ingest.service import meta_label
from ..models import Case, Evidence, FindingRow, JsonMixin, Review

UI_KEY = {"none": "none", "inconclusive": "inc", "indicators": "ind", "strong": "strong"}
ICON = {"video": "movie", "audio": "graphic_eq", "image": "image", "text": "notes", "cross-modal": "join_inner"}
MOD_LABEL = {"video": "Video", "audio": "Audio", "image": "Image", "text": "Text", "cross-modal": "Cross-modal"}


def verdict(v: Optional[dict]) -> Optional[dict]:
    if not v:
        return None
    return {"key": UI_KEY[v["band"]], "band": v["band"], "label": config.VERDICT_LABELS[v["band"]],
            "lo": v["lo"], "hi": v["hi"], "p": v.get("p"), "why": v.get("why", ""), "corroborated": v.get("corroborated", False)}


def deepfake(v: Optional[dict]) -> Optional[dict]:
    """The deepfake assessment as the UI shows it: Likely deepfake / Likely authentic / Uncertain, with P and range."""
    d = (v or {}).get("deepfake")
    if not d:
        if not v:
            return None
        return {"key": "uncertain", "label": "Uncertain", "p": None, "lo": None, "hi": None,
                "why": "This analysis has no AI-generation assessment. Re-run analysis to assess it.",
                "calibrated": False, "requires_rerun": True}
    from ..scoring.deepfake import ASSESSMENT_VERSION
    if d.get("version") != ASSESSMENT_VERSION:
        return {"key": "uncertain", "label": "Uncertain", "p": None, "lo": None, "hi": None,
                "why": "This analysis uses an older scoring method. Re-run analysis for a separate AI-generation assessment.",
                "calibrated": False, "requires_rerun": True}
    return {"version": d["version"], "key": d["label"], "label": d["text"], "p": d.get("p"), "lo": d.get("lo"), "hi": d.get("hi"),
            "why": d.get("why", ""), "driver": d.get("driver"), "calibrated": d.get("calibrated", False),
            "ai": d.get("ai"), "manipulation": d.get("manipulation")}


def latest_reviews(s: Session, case_id: str) -> dict[str, Review]:
    out: dict[str, Review] = {}
    for r in s.exec(select(Review).where(Review.case_id == case_id).order_by(Review.id)):
        out[r.finding_id] = r
    return out


def display_name(ev: Evidence) -> str:
    if ev.kind == "text":
        return ev.filename if ev.filename.startswith("Caption") else f"Text · {ev.filename}"
    return ev.filename


def evidence_summary(ev: Evidence, n_findings: int = 0) -> dict[str, Any]:
    meta = JsonMixin.loads(ev.metadata_json, {})
    return {"id": ev.id, "label": ev.label, "case_id": ev.case_id, "kind": ev.kind, "icon": ICON[ev.kind],
            "filename": ev.filename, "display_name": display_name(ev), "meta_label": meta_label(ev.kind, ev.size, meta),
            "sha256": ev.sha256, "sha_short": custody.short(ev.sha256), "size": ev.size, "mime": ev.mime,
            "status": ev.status, "derived_from": meta.get("derived_from"), "verdict": verdict(JsonMixin.loads(ev.verdict_json)),
            "deepfake": deepfake(JsonMixin.loads(ev.verdict_json)),
            "warnings": meta.get("warnings", []), "findings_count": n_findings,
            "media_url": f"/api/evidence/{ev.id}/media", "thumb_url": f"/api/evidence/{ev.id}/thumb",
            "duration": meta.get("duration"), "width": meta.get("width"), "height": meta.get("height"),
            "fps": meta.get("fps"), "sample_rate": meta.get("sample_rate"), "created_at": ev.created_at.isoformat()}


def _loc_icon(loc: dict) -> str:
    return {"frame_range": "schedule", "time_range": "schedule", "bbox": "crop_free", "mask": "crop_free",
            "text_span": "data_object", "file": "data_object"}.get(loc.get("type", ""), "my_location")


def finding(f: FindingRow, ev: Evidence, review: Optional[Review]) -> dict[str, Any]:
    loc = JsonMixin.loads(f.location_json, {})
    extra = JsonMixin.loads(f.extra_json, {})
    seek = loc.get("start") if loc.get("type") in ("frame_range", "time_range") else None
    goto = {"image": "image", "audio": "audio"}.get(ev.kind)
    return {"id": f.id, "finding_id": f.finding_id, "evidence_id": ev.label, "evidence_db_id": ev.id,
            "evidence_kind": ev.kind, "modality": f.modality, "mod_label": MOD_LABEL[f.modality], "icon": ICON[f.modality],
            "indicator": f.indicator, "family": f.family, "name": f.name, "location": loc, "loc_label": f.loc_label,
            "loc_icon": _loc_icon(loc), "t": seek, "raw_score": f.raw_score, "score": f.score,
            "conf_low": f.conf_low, "conf_high": f.conf_high, "confidence_range": [f.conf_low, f.conf_high],
            "band": f.band, "verdict": {"key": UI_KEY[f.band], "label": config.VERDICT_LABELS[f.band]},
            "method": f.method, "explanation": f.explanation, "alternatives": JsonMixin.loads(f.alternatives_json, []),
            "artifacts": [f"/api/evidence/{ev.id}/artifacts/{a.split('/', 1)[1]}" for a in JsonMixin.loads(f.artifacts_json, [])],
            "compare": extra.get("compare"), "calibrated": extra.get("calibrated", False),
            "weakened": extra.get("weight_scale", 1.0) < 1.0, "extra": extra, "goto": goto,
            "review": {"status": review.decision if review else "pending", "note": review.note if review else None,
                       "decided_at": review.created_at.isoformat() if review else None,
                       "reviewer": review.reviewer if review else None}}


def case_findings(s: Session, case_id: str) -> list[dict[str, Any]]:
    evs = {e.id: e for e in s.exec(select(Evidence).where(Evidence.case_id == case_id))}
    reviews = latest_reviews(s, case_id)
    rows = s.exec(select(FindingRow).where(FindingRow.case_id == case_id).order_by(FindingRow.sort_key))
    return [finding(f, evs[f.evidence_id], reviews.get(f.finding_id)) for f in rows]


def case_summary(s: Session, c: Case) -> dict[str, Any]:
    evs = list(s.exec(select(Evidence).where(Evidence.case_id == c.id).order_by(Evidence.order_idx)))
    finding_ids = [f.finding_id for f in s.exec(select(FindingRow).where(FindingRow.case_id == c.id))]
    reviews = latest_reviews(s, c.id)
    pending = sum(1 for fid in finding_ids if fid not in reviews or reviews[fid].decision == "pending")
    v = verdict(JsonMixin.loads(c.overall_verdict_json))
    if v is None or c.status != "analyzed":
        why = {"draft": f"{len(evs)} evidence item{'s' if len(evs) != 1 else ''} added, not analyzed yet",
               "queued": "analysis queued", "running": "analysis running", "failed": "analysis failed, see the run log"}
        v = {"key": "review", "band": None, "label": "Needs review", "lo": None, "hi": None,
             "why": why.get(c.status, "not analyzed yet"), "corroborated": False}
    kinds = []
    for e in evs:
        if e.kind not in kinds and not JsonMixin.loads(e.metadata_json, {}).get("derived_from"):
            kinds.append(e.kind)
    return {"id": c.id, "title": c.title, "description": c.description, "investigator": c.investigator,
            "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat(), "status": c.status,
            "closed": c.closed, "types": [ICON[k] for k in kinds], "kinds": kinds, "verdict": v, "why": v["why"],
            "deepfake": deepfake(JsonMixin.loads(c.overall_verdict_json)) if c.status == "analyzed" else None,
            "findings_count": len(finding_ids), "pending_review": pending,
            "needs_review": c.status == "analyzed" and pending > 0, "evidence_count": len(evs),
            "analysis_seconds": c.analysis_seconds, "run_count": c.run_count}


def case_detail(s: Session, c: Case) -> dict[str, Any]:
    out = case_summary(s, c)
    evs = list(s.exec(select(Evidence).where(Evidence.case_id == c.id).order_by(Evidence.order_idx)))
    counts: dict[int, int] = {}
    for f in s.exec(select(FindingRow).where(FindingRow.case_id == c.id)):
        counts[f.evidence_id] = counts.get(f.evidence_id, 0) + 1
    out["evidence"] = [evidence_summary(e, counts.get(e.id, 0)) for e in evs]
    out["limitations"] = JsonMixin.loads(c.limitations_json, config.GENERAL_LIMITATIONS)
    return out


def exif_rows(ev: Evidence, findings: list[dict], case_findings_: list[dict]) -> list[dict]:
    """EXIF table for the image viewer, with conflict notes pointing at the findings that use each field."""
    m = JsonMixin.loads(ev.metadata_json, {})
    exif = m.get("exif", {})
    by_field = {f["location"].get("field"): f for f in findings if f["location"].get("type") == "file"}
    date_conf = next((f for f in case_findings_ if f["indicator"] == "claim_date_conflict"
                      and f["extra"].get("target_evidence") == ev.label), None)

    def note(field: str) -> Optional[str]:
        f = by_field.get(field)
        return f"{f['name']} ({f['finding_id']})" if f else None

    gps = m.get("gps")
    thumb = m.get("thumbnail")
    rows = [
        ("Make / Model", " ".join(x for x in (exif.get("Make"), exif.get("Model")) if x) or "not present", note("Make")),
        ("DateTimeOriginal", exif.get("DateTimeOriginal", "not present"),
         f"Caption gives {date_conf['compare'][0]['v']} ({date_conf['finding_id']})" if date_conf and date_conf.get("compare") else None),
        ("Software", exif.get("Software", "not present"), note("Software")),
        ("Image size", f"{m.get('width')} × {m.get('height')}", None),
        ("Thumbnail", f"{thumb['width']} × {thumb['height']}" if thumb and "width" in thumb else "not present", note("JPEGThumbnail")),
        ("JPEG quality (est.)", f"≈{m['jpeg_quality']}" if m.get("jpeg_quality") else "not JPEG", None),
        ("GPS", f"{gps['lat']}, {gps['lon']}" if gps else "not present", None),
        ("Color space", exif.get("ColorSpace", m.get("mode", "—")), None),
        ("File modified (EXIF)", exif.get("DateTime", "not present"), note("DateTime")),
    ]
    return [{"k": k, "v": v, "note": n, "conflict": bool(n)} for k, v, n in rows]

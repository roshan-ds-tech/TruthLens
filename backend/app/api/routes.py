"""REST API (design doc §5.2, served under /api — D-09), plus the read-only views the UI needs (D-04)."""
from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlmodel import Session, func, select

from .. import config, custody, db, jobs, registry
from ..auth import can_see, current_user
from ..ingest.service import IngestError, copy_upload_to_temp, ingest_file, ingest_text
from ..models import Case, CustodyLog, Evidence, FindingRow, Job, JsonMixin, ReportRow, Review, User, utcnow
from . import adapters

router = APIRouter(prefix="/api")


def get_session():
    with db.session() as s:
        yield s


def _case(s: Session, case_id: str, u: User) -> Case:
    c = s.get(Case, case_id)
    if c is None or not can_see(c, u):
        raise HTTPException(404, f"Case {case_id} not found")
    return c


def _evidence(s: Session, evidence_id: int, u: User) -> Evidence:
    ev = s.get(Evidence, evidence_id)
    if ev is None or not can_see(s.get(Case, ev.case_id), u):
        raise HTTPException(404, "Evidence not found")
    return ev


# ------------------------------------------------------------------ cases

class CaseIn(BaseModel):
    title: str
    investigator: Optional[str] = None
    description: str = ""


class CasePatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    closed: Optional[bool] = None


def next_case_id(s: Session) -> str:
    nums = [int(m.group(1)) for cid in s.exec(select(Case.id)).all() if (m := re.match(r"C-(\d+)$", cid))]
    return f"C-{(max(nums) + 1 if nums else 1):04d}"


@router.post("/cases")
def create_case(body: CaseIn, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "Case title is required")
    who = (body.investigator or u.name).strip()
    case = Case(id=next_case_id(s), title=title, description=body.description.strip(), investigator=who, owner_id=u.id)
    s.add(case)
    s.commit()
    custody.log(s, case.id, who, "Case opened", f"truthlens {config.APP_VERSION}", "—", f"case {custody.sha256_json([case.id, title])}")
    return adapters.case_detail(s, case)


@router.get("/cases")
def list_cases(s: Session = Depends(get_session), u: User = Depends(current_user)) -> list[dict]:
    rows = s.exec(select(Case).order_by(Case.updated_at.desc(), Case.id.desc())).all()  # type: ignore[attr-defined]
    return [adapters.case_summary(s, c) for c in rows if can_see(c, u)]


@router.get("/cases/{case_id}")
def get_case(case_id: str, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    return adapters.case_detail(s, _case(s, case_id, u))


@router.patch("/cases/{case_id}")
def patch_case(case_id: str, body: CasePatch, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    c = _case(s, case_id, u)
    for k in ("title", "description", "closed"):
        v = getattr(body, k)
        if v is not None:
            setattr(c, k, v)
    c.updated_at = utcnow()
    s.add(c)
    s.commit()
    return adapters.case_detail(s, c)


# ------------------------------------------------------------------ evidence

@router.post("/cases/{case_id}/evidence")
async def upload_evidence(case_id: str, file: Optional[UploadFile] = File(None), text: Optional[str] = Form(None),
                          source: Optional[str] = Form(None), s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    c = _case(s, case_id, u)
    who = c.investigator
    try:
        if file is not None:
            tmp = copy_upload_to_temp(file.file, Path(file.filename or "").suffix)
            try:
                ev = ingest_file(s, c, tmp, Path(file.filename or "upload").name, who)
            finally:
                tmp.unlink(missing_ok=True)
        elif text is not None:
            ev = ingest_text(s, c, text, who, source or "Pasted caption or claim")
        else:
            raise HTTPException(400, "Send a file or a text field")
    except IngestError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    if c.status == "analyzed":
        c.status = "draft"   # new evidence: the verdict is stale until the next run
        s.add(c)
        s.commit()
    return adapters.evidence_summary(ev)


@router.get("/evidence")
def library(s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    visible = {c.id for c in s.exec(select(Case)).all() if can_see(c, u)}
    evs = [e for e in s.exec(select(Evidence).order_by(Evidence.created_at.desc(), Evidence.id.desc())).all()  # type: ignore[attr-defined]
           if e.case_id in visible]
    counts = dict(s.exec(select(FindingRow.evidence_id, func.count()).group_by(FindingRow.evidence_id)).all())
    items = [adapters.evidence_summary(e, counts.get(e.id, 0)) for e in evs]
    return {"count": len(items), "total_bytes": sum(e.size for e in evs), "items": items}


@router.get("/evidence/{evidence_id}")
def evidence_detail(evidence_id: int, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    ev = _evidence(s, evidence_id, u)
    allf = adapters.case_findings(s, ev.case_id)
    mine = [f for f in allf if f["evidence_db_id"] == ev.id]
    out = adapters.evidence_summary(ev, len(mine))
    extra = JsonMixin.loads(ev.extra_json, {})
    out["metadata"] = JsonMixin.loads(ev.metadata_json, {})
    out["extra"] = {k: v for k, v in extra.items() if k not in ("transcript", "waveform")}
    out["findings"] = mine
    if ev.kind == "image":
        out["exif_rows"] = adapters.exif_rows(ev, mine, allf)
    if ev.kind == "text":
        out["text"] = custody.original_path(ev.case_id, ev.sha256).read_text("utf-8")
        out["claims"] = extra.get("claims", [])
    return out


@router.get("/evidence/{evidence_id}/findings")
def evidence_findings(evidence_id: int, s: Session = Depends(get_session), u: User = Depends(current_user)) -> list[dict]:
    ev = _evidence(s, evidence_id, u)
    return [f for f in adapters.case_findings(s, ev.case_id) if f["evidence_db_id"] == ev.id]


@router.get("/evidence/{evidence_id}/media")
def evidence_media(evidence_id: int, s: Session = Depends(get_session), u: User = Depends(current_user)):
    ev = _evidence(s, evidence_id, u)
    return FileResponse(custody.original_path(ev.case_id, ev.sha256), media_type=ev.mime,
                        headers={"Cache-Control": "private, max-age=3600"})


@router.get("/evidence/{evidence_id}/thumb")
def evidence_thumb(evidence_id: int, s: Session = Depends(get_session), u: User = Depends(current_user)):
    ev = _evidence(s, evidence_id, u)
    src = custody.original_path(ev.case_id, ev.sha256)
    cache = config.DERIVED_DIR / ev.case_id / ev.label / "thumb.jpg"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image, ImageOps

            if ev.kind == "image":
                with Image.open(src) as im:
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    im.thumbnail((480, 300))
                    im.save(cache, "JPEG", quality=82)
            elif ev.kind == "video":
                import cv2

                cap = cv2.VideoCapture(str(src))
                cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
                ok, frame = cap.read()
                cap.release()
                if not ok:
                    raise HTTPException(404, "No frame")
                im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                im.thumbnail((480, 300))
                im.save(cache, "JPEG", quality=82)
            else:
                raise HTTPException(404, "No thumbnail for this type")
        except HTTPException:
            raise
        except Exception as exc:  # unreadable media: the UI keeps its striped placeholder
            raise HTTPException(404, f"Thumbnail unavailable: {exc}") from exc
    return FileResponse(cache, media_type="image/jpeg")


@router.get("/evidence/{evidence_id}/artifacts/{name}")
def evidence_artifact(evidence_id: int, name: str, s: Session = Depends(get_session), u: User = Depends(current_user)):
    ev = _evidence(s, evidence_id, u)
    if "/" in name or ".." in name:
        raise HTTPException(400, "Bad artifact name")
    path = config.ARTIFACT_DIR / ev.case_id / ev.label / name
    if not path.exists():
        raise HTTPException(404, "Artifact not found (run the analysis first)")
    return FileResponse(path, media_type="image/png")


@router.get("/evidence/{evidence_id}/waveform")
def evidence_waveform(evidence_id: int, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    ev = _evidence(s, evidence_id, u)
    extra = JsonMixin.loads(ev.extra_json, {})
    wf = extra.get("waveform")
    if not wf:
        raise HTTPException(404, "Waveform not computed yet (run the analysis first)")
    return {**wf, "transcript": extra.get("transcript"), "bandlimit": extra.get("bandlimit"), "prosody": extra.get("prosody"),
            "spectrogram_url": f"/api/evidence/{ev.id}/artifacts/spectrogram.png"}


# ------------------------------------------------------------------ analysis

@router.post("/cases/{case_id}/analyze")
def analyze(case_id: str, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    c = _case(s, case_id, u)
    if not s.exec(select(Evidence).where(Evidence.case_id == case_id)).first():
        raise HTTPException(400, "Add evidence before starting the analysis")
    job = jobs.submit(case_id, c.investigator)
    return {"job_id": job.id, "case_id": case_id, "status": job.status}


def _job_out(job: Job) -> dict:
    items = JsonMixin.loads(job.progress_json, [])
    total = sum(len(i["steps"]) for i in items) or 1
    done = sum(1 for i in items for st in i["steps"] if st["status"] in ("done", "failed", "skipped"))
    end = job.finished_at or utcnow()
    start = job.started_at or job.created_at
    elapsed = max(0.0, (end.replace(tzinfo=None) - start.replace(tzinfo=None)).total_seconds())
    return {"id": job.id, "case_id": job.case_id, "status": job.status, "created_at": job.created_at.isoformat(),
            "elapsed_s": round(elapsed, 1), "progress": round(done / total, 3), "items": items,
            "log": JsonMixin.loads(job.log_json, []), "error": job.error, "findings_count": job.findings_count}


@router.get("/jobs/{job_id}")
def get_job(job_id: int, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    job = s.get(Job, job_id)
    if job is None or not can_see(s.get(Case, job.case_id), u):
        raise HTTPException(404, "Job not found")
    return _job_out(job)


@router.get("/cases/{case_id}/jobs/latest")
def latest_job(case_id: str, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    _case(s, case_id, u)
    job = s.exec(select(Job).where(Job.case_id == case_id).order_by(Job.id.desc())).first()  # type: ignore[attr-defined]
    if job is None:
        raise HTTPException(404, "No analysis has run for this case")
    return _job_out(job)


@router.get("/cases/{case_id}/findings")
def case_findings(case_id: str, s: Session = Depends(get_session), u: User = Depends(current_user)) -> list[dict]:
    _case(s, case_id, u)
    return adapters.case_findings(s, case_id)


@router.get("/cases/{case_id}/findings/{finding_id}/thumb")
def finding_thumb(case_id: str, finding_id: str, s: Session = Depends(get_session), u: User = Depends(current_user)):
    """The evidence crop a finding points at (region box, video frame or spectrogram slice), as PNG."""
    from ..report.render import thumb_image

    _case(s, case_id, u)
    f = next((x for x in adapters.case_findings(s, case_id) if x["finding_id"] == finding_id), None)
    if f is None:
        raise HTTPException(404, "Finding not found")
    img = thumb_image(f, s.get(Evidence, f["evidence_db_id"]))
    if img is None:
        raise HTTPException(404, "No visual crop for this finding")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return Response(buf.getvalue(), media_type="image/png")


@router.get("/cases/{case_id}/graph")
def case_graph(case_id: str, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    return graph_for(s, _case(s, case_id, u))


def graph_for(s: Session, c: Case) -> dict:
    from ..correlate import graph as graph_mod
    from ..correlate import rules as rules_mod

    case_id = c.id
    findings = adapters.case_findings(s, case_id)
    evs = {e.label: e for e in s.exec(select(Evidence).where(Evidence.case_id == case_id))}
    rf = [rules_mod.F(f["finding_id"], f["evidence_id"], f["evidence_kind"], None, f["modality"], f["indicator"],
                      f["family"], f["location"], f["score"], f["extra"]) for f in findings]
    from ..models import Correlation

    edges = [rules_mod.Edge(r.rule_id, r.rule_name, r.from_finding, r.to_finding, r.relation.replace("_weak", ""), r.note,
                            weak=r.relation.endswith("_weak"))
             for r in s.exec(select(Correlation).where(Correlation.case_id == case_id).order_by(Correlation.id))]
    out = graph_mod.export(rf, edges, {k: e.kind for k, e in evs.items()})
    out["combined"] = adapters.verdict(JsonMixin.loads(c.overall_verdict_json))
    return out


# ------------------------------------------------------------------ review

class ReviewIn(BaseModel):
    decision: Optional[Literal["accepted", "rejected", "pending"]] = None
    note: Optional[str] = None


@router.patch("/findings/{finding_db_id}/review")
def review_finding(finding_db_id: int, body: ReviewIn, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    f = s.get(FindingRow, finding_db_id)
    if f is None:
        raise HTTPException(404, "Finding not found")
    case = _case(s, f.case_id, u)
    prev = adapters.latest_reviews(s, f.case_id).get(f.finding_id)
    decision = body.decision or (prev.decision if prev else "pending")
    note = body.note if body.note is not None else (prev.note if prev else None)
    s.add(Review(case_id=f.case_id, finding_id=f.finding_id, reviewer=case.investigator, decision=decision,
                 note=(note or None)))
    s.commit()
    reviews = adapters.latest_reviews(s, f.case_id)
    state = custody.sha256_json({k: [r.decision, r.note] for k, r in sorted(reviews.items())})
    last_run = s.exec(select(CustodyLog).where(CustodyLog.case_id == f.case_id, CustodyLog.action.like("Analysis run%"))
                      .order_by(CustodyLog.id.desc())).first()  # type: ignore[attr-defined]
    what = f"{f.finding_id} {decision}" if body.decision else f"{f.finding_id} note {'edited' if note else 'cleared'}"
    custody.log(s, f.case_id, case.investigator, what, "review ui", last_run.output_hash if last_run else "—", f"review {state}")
    ev = s.get(Evidence, f.evidence_id)
    return adapters.finding(f, ev, reviews.get(f.finding_id))


# ------------------------------------------------------------------ custody, report

@router.get("/cases/{case_id}/custody")
def case_custody(case_id: str, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    return custody_for(s, _case(s, case_id, u).id)


def custody_for(s: Session, case_id: str) -> dict:
    rows = custody.entries(s, case_id)
    return {"chain_valid": custody.verify_chain(rows),
            "entries": [{"id": r.id, "ts": r.ts.isoformat(), "actor": r.actor, "action": r.action, "tool": r.tool_version,
                         "input_hash": r.input_hash, "output_hash": r.output_hash, "entry_hash": r.entry_hash} for r in rows]}


@router.post("/cases/{case_id}/report")
def build_report(case_id: str, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    from ..report import render

    c = _case(s, case_id, u)
    if c.status != "analyzed":
        raise HTTPException(409, "Run the analysis before exporting a report")
    return render.build(s, c)


def _latest_report(s: Session, case_id: str) -> ReportRow:
    r = s.exec(select(ReportRow).where(ReportRow.case_id == case_id).order_by(ReportRow.id.desc())).first()  # type: ignore[attr-defined]
    if r is None:
        raise HTTPException(404, "No report yet")
    return r


@router.get("/cases/{case_id}/report")
def get_report(case_id: str, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    _case(s, case_id, u)
    r = _latest_report(s, case_id)
    data = json.loads(Path(r.path_json).read_text())
    data["files"] = {"pdf": f"/api/cases/{case_id}/report.pdf" if r.path_pdf else None,
                     "json": f"/api/cases/{case_id}/report.json", "html": f"/api/cases/{case_id}/report.html"}
    return data


@router.get("/cases/{case_id}/report.{fmt}")
def download_report(case_id: str, fmt: Literal["pdf", "json", "html"], s: Session = Depends(get_session), u: User = Depends(current_user)):
    _case(s, case_id, u)
    r = _latest_report(s, case_id)
    path = {"pdf": r.path_pdf, "json": r.path_json, "html": r.path_html}[fmt]
    if not path or not Path(path).exists():
        raise HTTPException(404, f"{fmt.upper()} report not available")
    media = {"pdf": "application/pdf", "json": "application/json", "html": "text/html"}[fmt]
    return FileResponse(path, media_type=media, filename=f"TruthLens_{case_id}_report.{fmt}" if fmt != "html" else None)


# ------------------------------------------------------------------ dashboard, validation, settings

@router.get("/stats")
def stats(s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    cases = [c for c in s.exec(select(Case)).all() if can_see(c, u)]
    ids = {c.id for c in cases}
    active = [c for c in cases if not c.closed]
    week = utcnow().replace(tzinfo=None) - timedelta(days=7)
    pending_by_case: dict[str, int] = {}
    for c in active:
        pending_by_case[c.id] = adapters.case_summary(s, c)["pending_review"]
    top = max(pending_by_case.items(), key=lambda kv: (kv[1], kv[0]), default=(None, 0))
    timed = [c.analysis_seconds for c in cases if c.analysis_seconds]
    kinds = sorted({k for k, cid in s.exec(select(Evidence.kind, Evidence.case_id)).all() if cid in ids})
    return {"active_cases": len(active), "closed_cases": len(cases) - len(active),
            "opened_this_week": sum(1 for c in cases if c.created_at.replace(tzinfo=None) >= week),
            "evidence_count": sum(1 for e in s.exec(select(Evidence.case_id)).all() if e in ids), "evidence_kinds": kinds,
            "pending_review": sum(pending_by_case.values()), "top_pending_case": {"id": top[0], "count": top[1]},
            "avg_analysis_seconds": round(sum(timed) / len(timed)) if timed else None}


@router.get("/validation/metrics")
def validation_metrics() -> dict:
    if not config.METRICS_PATH.exists():
        raise HTTPException(404, "No validation run yet. Run `make validate`.")
    return json.loads(config.METRICS_PATH.read_text())


def models_lock() -> str:
    h = hashlib.sha256()
    if config.REQUIREMENTS_PATH.exists():
        h.update(config.REQUIREMENTS_PATH.read_bytes())
    if config.MODEL_DIR.exists():
        for p in sorted(config.MODEL_DIR.rglob("*")):
            if p.is_file():
                h.update(f"{p.relative_to(config.MODEL_DIR)}:{p.stat().st_size}".encode())
    return h.hexdigest()


def _user_bytes(s: Session, u: User) -> int:
    visible = {c.id for c in s.exec(select(Case)).all() if can_see(c, u)}
    return sum(size for size, cid in s.exec(select(Evidence.size, Evidence.case_id)).all() if cid in visible)


class SettingsIn(BaseModel):
    investigator: Optional[str] = None
    analyzers: Optional[dict[str, bool]] = None


def _settings(s: Session, u: User) -> dict[str, Any]:
    enabled = registry.enabled_map(s, u.id)
    return {"investigator": u.name, "email": u.email, "mode": config.MODE,
            "analyzers": [{"key": a.key, "name": a.name, "desc": a.desc, "version": a.version, "kinds": list(a.kinds),
                           "enabled": enabled[a.key], "available": registry.dependency_available(a)}
                          for a in registry.ALL.values()],
            "models_lock": models_lock(),
            "vault": {"path": "server evidence store" if config.MODE == "hosted" else str(config.EVIDENCE_DIR),
                      "bytes": _user_bytes(s, u)},
            "versions": registry.versions(), "app_version": config.APP_VERSION}


@router.get("/settings")
def get_settings(s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    return _settings(s, u)


@router.put("/settings")
def put_settings(body: SettingsIn, s: Session = Depends(get_session), u: User = Depends(current_user)) -> dict:
    if body.analyzers:
        registry.set_enabled(s, body.analyzers, u.id)
    if body.investigator and body.investigator.strip():
        u.name = body.investigator.strip()[:80]
        s.add(u)
        s.commit()
    return _settings(s, u)


@router.get("/health")
def health() -> dict:
    return {"ok": True, "version": config.APP_VERSION, "mode": config.MODE}

"""Case analysis: run analyzers per evidence item, correlate, score, persist, log custody.

A failing analyzer never fails the case: its step is marked failed, the error goes to the live log,
and it becomes a listed limitation. Finding IDs are assigned only after every analyzer has run, in a
fixed order, so rerunning the same originals gives identical IDs and scores (D-06).
"""
from __future__ import annotations

import gc
import shutil
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlmodel import Session, delete, select

from . import config, custody, registry
from .analyzers import video as video_mod
from .analyzers.base import AnalysisContext, RawFinding, fmt_t
from .correlate import graph as graph_mod
from .correlate import lipsync
from .correlate import rules as rules_mod
from .models import Case, Correlation, Evidence, FindingRow, Job, JsonMixin, utcnow
from .scoring import calibrate, fuse
from .scoring import deepfake as deepfake_score

REPORT_FLOOR = 0.30
PREFIX = {"image": "IMG", "video": "VID", "audio": "AUD", "text": "TXT", "cross-modal": "XM"}
KIND_ORDER = {"video": 0, "audio": 1, "image": 2, "text": 3}
NOUN = {"video": "Video", "audio": "Audio", "image": "Image", "text": "Text"}
ICON = {"video": "movie", "audio": "graphic_eq", "image": "image", "text": "notes"}


class Tracker:
    """Writes per-step progress and the live log to the job row the Analysis screen polls."""

    def __init__(self, s: Session, job: Optional[Job]):
        self.s, self.job = s, job
        self.items: list[dict] = []
        self.lines: list[dict] = []
        self.t0 = time.monotonic()

    def log(self, src: str, msg: str) -> None:
        self.lines.append({"t": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3], "src": src, "msg": msg})
        self.flush()

    def flush(self) -> None:
        if not self.job:
            return
        self.job.progress_json = JsonMixin.dumps(self.items)
        self.job.log_json = JsonMixin.dumps(self.lines[-400:])
        self.s.add(self.job)
        self.s.commit()

    def set_step(self, item: int, step: int, status: str) -> None:
        self.items[item]["steps"][step]["status"] = status
        self.flush()


def _scrub(text: str) -> str:
    """Error text for the UI: absolute file paths replaced, so server layout is not exposed."""
    import re

    return re.sub(r"(?:/[^\s/:'\"]+){2,}", "<file>", text)


def _ordered(evs: list[Evidence]) -> list[Evidence]:
    return sorted(evs, key=lambda e: (KIND_ORDER[e.kind], e.order_idx))


def _context(case_id: str, ev: Evidence, log: Callable[[str, str], None]) -> AnalysisContext:
    art = config.ARTIFACT_DIR / case_id / ev.label
    return AnalysisContext(case_id=case_id, evidence_id=ev.id, label=ev.label, kind=ev.kind, filename=ev.filename,
                           sha256=ev.sha256, original=custody.original_path(case_id, ev.sha256),
                           derived_dir=config.DERIVED_DIR / case_id / ev.label, artifact_dir=art,
                           metadata=JsonMixin.loads(ev.metadata_json, {}), log=log)


def _persistable(extra: dict) -> dict:
    return {k: v for k, v in extra.items() if not k.startswith("_")}


def _why(findings: list[dict], edges: list[rules_mod.Edge], by_id: dict[str, dict], band: str,
         failed: list[str]) -> str:
    """One-line 'Why' generated from the strongest rules and findings (structured, not free text)."""
    parts: list[str] = []
    for e in sorted(edges, key=lambda e: (e.relation != "supports", e.weak, e.rule_id)):
        if e.relation != "supports" or e.weak:
            continue
        a, b = by_id.get(e.source), by_id.get(e.target)
        if e.rule_id == "R-03" and a and b:
            parts.append(f"an audio splice at {a['loc_time']} lines up with a motion break at {b['loc_time']}")
        elif e.rule_id == "R-11" and a:
            parts.append(f"the caption date conflicts with the capture metadata of {a['extra'].get('target_evidence', 'another item')}")
        elif e.rule_id == "R-05":
            parts.append("the caption quotes words that are not in the speech")
        elif e.rule_id == "R-09":
            parts.append("an image region and the video's flagged face region point at the same area")
        if len(parts) == 2:
            break
    if not parts:
        top = sorted((f for f in findings if f["band"] != "none"), key=lambda f: -f["score"])[:2]
        parts = [f"{f['name'].lower()} ({f['loc_label']})" for f in top]
    if not parts:
        if failed:
            return f"no indicator crossed its threshold, but {', '.join(failed)} could not run"
        return "no analyzer found an indicator above its threshold"
    text = " and ".join(parts) if len(parts) == 2 else parts[0]
    if band == "inconclusive":
        text += "; the signals are weak or not corroborated"
    return text


def run_case(s: Session, case_id: str, job: Optional[Job] = None, actor: str = "system") -> dict[str, Any]:
    started = time.monotonic()
    case = s.get(Case, case_id)
    if case is None:
        raise ValueError(f"case {case_id} not found")
    evs = _ordered(list(s.exec(select(Evidence).where(Evidence.case_id == case_id))))
    if not evs:
        raise ValueError("case has no evidence")
    enabled = registry.enabled_map(s, case.owner_id)
    tr = Tracker(s, job)
    case.status = "running"
    s.add(case)
    if job:
        job.status, job.started_at = "running", utcnow()
    for ev in evs:
        steps = registry.steps_for(ev.kind)
        meta = JsonMixin.loads(ev.metadata_json, {})
        tr.items.append({"evidence": ev.label, "name": ev.filename, "icon": ICON[ev.kind], "kind": ev.kind,
                         "meta": _meta_label(ev, meta), "sha": custody.short(ev.sha256),
                         "steps": [{"key": a.key, "label": a.step, "status": "queued"} for a in steps],
                         "started": None, "finished": None})
    run_no = case.run_count + 1
    tr.log("run", f"tl-analyze {config.APP_VERSION} · run {run_no} · seed {config.SEED} · calibration {calibrate.table_version()}")

    # clean previous results; originals and custody are never touched
    s.exec(delete(FindingRow).where(FindingRow.case_id == case_id))
    s.exec(delete(Correlation).where(Correlation.case_id == case_id))
    s.commit()
    shutil.rmtree(config.ARTIFACT_DIR / case_id, ignore_errors=True)
    shutil.rmtree(config.DERIVED_DIR / case_id, ignore_errors=True)
    calibrate.reload()
    deepfake_score.reload()

    contexts: list[AnalysisContext] = []
    shared: dict[str, Any] = {}
    for ev in evs:
        if not custody.verify_original(case_id, ev.sha256):
            raise RuntimeError(f"original of {ev.label} failed its hash check")
        tr.log("ingest", f"verified sha256 {custody.short(ev.sha256)} (read-only) · {ev.label}")
        ctx = _context(case_id, ev, lambda src, msg: tr.log(src, msg))
        ctx.shared = shared
        contexts.append(ctx)
    for ctx in contexts:
        ctx.case_evidence = contexts

    raw: list[tuple[AnalysisContext, int, RawFinding]] = []
    limitations: list[str] = []
    failed_detectors: dict[str, list[str]] = {}
    for item, (ev, ctx) in enumerate(zip(evs, contexts)):
        ev.status = "analyzing"
        s.add(ev)
        tr.items[item]["started"] = round(time.monotonic() - tr.t0, 2)
        for w in ctx.metadata.get("warnings", []):
            limitations.append(f"{ev.label}: {w}")
        for si, step in enumerate(registry.steps_for(ev.kind)):
            if not enabled.get(step.key, True):
                tr.set_step(item, si, "skipped")
                tr.log(ev.kind, f"{step.name} skipped on {ev.label}: turned off in Settings")
                limitations.append(f"{step.name} was turned off in Settings and did not run on {ev.label}.")
                continue
            if not registry.dependency_available(step):
                tr.set_step(item, si, "skipped")
                tr.log(ev.kind, f"{step.name} skipped on {ev.label}: {step.optional_dep} is not installed")
                limitations.append(f"{step.name} did not run on {ev.label} ({step.optional_dep} is not installed).")
                if step.key not in registry.DATA_STEPS | registry.AI_STEPS:
                    failed_detectors.setdefault(ev.label, []).append(step.name)
                continue
            tr.set_step(item, si, "running")
            try:
                found = step.run(ctx)
                for f in found:
                    raw.append((ctx, si, f))
                    if f.raw_score >= 0.5:
                        tr.log(ev.kind, f"{f.name.lower()} · {f.loc_label}")
                tr.set_step(item, si, "done")
            except Exception as exc:  # noqa: BLE001 - isolate every analyzer
                tr.set_step(item, si, "failed")
                msg = f"{exc.__class__.__name__}: {_scrub(str(exc))[:160]}"
                tr.log(ev.kind, f"{step.name} failed on {ev.label} · {msg}")
                if step.key in registry.AI_STEPS:
                    limitations.append(f"{step.name} did not run on {ev.label} ({msg}); the deepfake probability for "
                                       f"{ev.label} rests on the manipulation evidence only.")
                else:
                    limitations.append(f"{step.name} failed on {ev.label} ({msg}); its signal is missing from the verdict.")
                if step.key not in registry.DATA_STEPS | registry.AI_STEPS:
                    failed_detectors.setdefault(ev.label, []).append(step.name)
                traceback.print_exc()
            gc.collect()
        if ev.kind == "video":
            ctx.extra["suspicion_curve"] = video_mod.suspicion_curve(ctx, [f for c, _, f in raw if c is ctx])
        tr.items[item]["finished"] = round(time.monotonic() - tr.t0, 2)
        ev.status = "analyzed"
        s.add(ev)
        tr.flush()

    # cross-modal measurement: lip-sync between a video and its own audio track
    for vctx in (c for c in contexts if c.kind == "video"):
        mouth = shared.get("mouth", {}).get(vctx.label)
        actx = next((c for c in contexts if c.metadata.get("derived_from") == vctx.label), None)
        if mouth and actx and enabled.get("face_flicker", True):
            try:
                for f in lipsync.findings(vctx, actx, mouth):
                    raw.append((vctx, 99, f))
                    tr.log("xmodal", f"lip-sync {f.loc_label} · {f.extra['min_r']:.2f} vs {f.extra['median_r']:.2f}")
            except Exception as exc:  # noqa: BLE001
                limitations.append(f"Lip-sync measurement failed ({exc.__class__.__name__}).")

    # deterministic IDs
    order = {ctx.label: i for i, ctx in enumerate(contexts)}
    raw.sort(key=lambda r: (order[r[0].label], r[1], round(r[2].sort, 4), r[2].indicator, r[2].loc_label))
    counters: dict[str, int] = {}
    scored: list[dict] = []
    for ctx, si, f in raw:
        modality = "cross-modal" if f.family == "lipsync" else ctx.kind
        pre = PREFIX[modality]
        counters[pre] = counters.get(pre, 0) + 1
        if f.extra.get("detector"):   # learned deepfake detectors use their own real-vs-AI calibration
            d = deepfake_score.calibrate(f.family, f.raw_score)
            cal = calibrate.Calibrated(round(d["p"], 4), round(d["lo"], 4), round(d["hi"], 4), d["calibrated"])
        else:
            cal = calibrate.calibrate(f.indicator, f.raw_score)
        loc = f.location
        loc_time = fmt_t(loc["start"]) if loc.get("start") is not None and loc["type"] in ("frame_range", "time_range") else ""
        scored.append({"finding_id": f"F-{pre}-{counters[pre]:03d}", "ctx": ctx, "evidence_id": ctx.evidence_id,
                       "evidence": ctx.label, "modality": modality, "indicator": f.indicator, "family": f.family,
                       "name": f.name, "location": loc, "loc_label": f.loc_label, "loc_time": loc_time,
                       "raw_score": round(f.raw_score, 4), "score": cal.p, "lo": cal.lo, "hi": cal.hi,
                       "calibrated": cal.calibrated, "method": f.method, "explanation": f.explanation,
                       "alternatives": list(f.alternatives), "artifacts": list(f.artifacts), "extra": dict(f.extra),
                       "weight_scale": 1.0, "sort_key": f"{order[ctx.label]:03d}-{si:02d}-{f.sort:012.4f}"})
    # findings whose whole range sits below the reporting floor are logged, not listed
    hidden = [f for f in scored if f["hi"] < REPORT_FLOOR]
    if hidden:
        scored = [f for f in scored if f["hi"] >= REPORT_FLOOR]
        for f in hidden:
            tr.log(f["ctx"].kind, f"below reporting floor: {f['name'].lower()} · {f['loc_label']} ({f['lo']:.2f}–{f['hi']:.2f})")
        limitations.append(f"{len(hidden)} weak signal{'s' if len(hidden) != 1 else ''} with a range entirely below "
                           f"{REPORT_FLOOR:.2f} {'were' if len(hidden) != 1 else 'was'} logged but not listed as findings.")
        counters = {}
        for f in scored:   # renumber so IDs stay consecutive (still deterministic)
            pre = f["finding_id"].split("-")[1]
            counters[pre] = counters.get(pre, 0) + 1
            f["finding_id"] = f"F-{pre}-{counters[pre]:03d}"
    if any(not f["calibrated"] for f in scored):
        names = sorted({f["indicator"] for f in scored if not f["calibrated"]})
        limitations.append("Uncalibrated indicators (no validation data yet): " + ", ".join(names) + ". Their ranges use a fixed ±0.12.")

    # correlation
    by_id = {f["finding_id"]: f for f in scored}
    parents = {c.label: c.metadata.get("derived_from") for c in contexts}
    rf = [rules_mod.F(f["finding_id"], f["evidence"], f["ctx"].kind, parents.get(f["evidence"]), f["modality"],
                      f["indicator"], f["family"], f["location"], f["score"], f["extra"]) for f in scored]
    evmap = {c.label: rules_mod.Ev(c.label, c.kind, parents.get(c.label), c.metadata, c.extra) for c in contexts}
    edges = rules_mod.run(rf, evmap)
    for e in edges:
        for fid, k in e.weight_scale.items():
            by_id[fid]["weight_scale"] *= k
        if e.alternative and e.alternative[0] in by_id and e.alternative[1] not in by_id[e.alternative[0]]["alternatives"]:
            by_id[e.alternative[0]]["alternatives"].insert(0, e.alternative[1])
        tr.log("correl", f"{e.rule_id} {e.relation}: {e.note}")
    for f in scored:
        f["band"] = fuse.finding_band(f["score"], f["lo"], f["hi"])
    fam = {f["finding_id"]: f["family"] for f in scored}

    def signals(fs: list[dict]) -> list[fuse.Signal]:
        # manipulation evidence only: the learned deepfake detectors are combined separately (scoring/deepfake.py)
        return [fuse.Signal(f["finding_id"], f["family"], f["score"], f["lo"], f["hi"], f["weight_scale"])
                for f in fs if not f["family"].startswith("ai_")]

    deepfake_items: dict[str, dict] = {}

    # per-evidence verdicts
    for ev, ctx in zip(evs, contexts):
        mine = [f for f in scored if f["evidence"] == ev.label]
        mine_ids = {f["finding_id"] for f in mine}
        internal = [e for e in edges if e.source in mine_ids and e.target in mine_ids]
        fz = fuse.fuse(signals(mine), rules_mod.independent_supports(internal, fam))
        failed = failed_detectors.get(ev.label, [])
        b = fz.band
        if b == "none" and failed:
            b = "inconclusive"
        why = _why(mine, internal, by_id, b, failed)
        manip_n = sum(1 for f in mine if not f["family"].startswith("ai_"))
        dfa = deepfake_score.assess_item(ctx.extra.get("ai_detector"),
                                         {"p": fz.p, "lo": fz.lo, "hi": fz.hi, "findings": manip_n}, ev.kind,
                                         (ctx.extra.get("ai_detector") or {}).get("words"))
        deepfake_items[ev.label] = dfa
        ev.verdict_json = JsonMixin.dumps({"band": b, "p": fz.p, "lo": fz.lo, "hi": fz.hi, "corroborated": fz.corroborated,
                                           "why": why, "families": fz.families, "deepfake": dfa})
        ev.extra_json = JsonMixin.dumps(_persistable(ctx.extra))
        s.add(ev)

    # case verdict
    supports = rules_mod.independent_supports(edges, fam)
    cz = fuse.fuse(signals(scored), supports)
    all_failed = [f"{n} ({lbl})" for lbl, names in failed_detectors.items() for n in names]
    case_band = "inconclusive" if cz.band == "none" and all_failed else cz.band
    case_why = _why(scored, edges, by_id, case_band, all_failed)
    case.overall_verdict_json = JsonMixin.dumps({"band": case_band, "p": cz.p, "lo": cz.lo, "hi": cz.hi,
                                                 "corroborated": cz.corroborated, "why": case_why,
                                                 "independent_supports": supports, "families": cz.families,
                                                 "deepfake": deepfake_score.assess_case(deepfake_items)})
    seen: set[str] = set()
    case.limitations_json = JsonMixin.dumps([x for x in config.GENERAL_LIMITATIONS + limitations if not (x in seen or seen.add(x))])

    # persist
    for f in scored:
        s.add(FindingRow(case_id=case_id, evidence_id=f["evidence_id"], finding_id=f["finding_id"], modality=f["modality"],
                         indicator=f["indicator"], family=f["family"], name=f["name"],
                         location_json=JsonMixin.dumps(f["location"]), loc_label=f["loc_label"], raw_score=f["raw_score"],
                         score=f["score"], conf_low=f["lo"], conf_high=f["hi"], band=f["band"], method=f["method"],
                         explanation=f["explanation"], alternatives_json=JsonMixin.dumps(f["alternatives"]),
                         artifacts_json=JsonMixin.dumps([f"{f['evidence']}/{a}" for a in f["artifacts"]]),
                         extra_json=JsonMixin.dumps(f["extra"] | {"calibrated": f["calibrated"],
                                                                  "weight_scale": f["weight_scale"]}),
                         sort_key=f["sort_key"]))
    for e in edges:
        s.add(Correlation(case_id=case_id, rule_id=e.rule_id, rule_name=e.rule_name, from_finding=e.source,
                          to_finding=e.target, relation=e.relation + ("_weak" if e.weak else ""), note=e.note))
    case.status = "analyzed"
    case.run_count = run_no
    case.analysis_seconds = round(time.monotonic() - started, 1)
    case.updated_at = utcnow()
    s.add(case)
    s.commit()

    digest = findings_digest(scored)
    in_hash = custody.sha256_json(sorted(ev.sha256 for ev in evs))
    graph = graph_mod.export(rf, edges, {c.label: c.kind for c in contexts})
    custody.log(s, case_id, actor, f"Analysis run {run_no}", f"tl-analyze {config.APP_VERSION} · calibration {calibrate.table_version()}",
                f"{len(evs)} evidence hashes {in_hash}", f"findings {digest}")
    tr.log("custody", f"findings {custody.short(digest)} appended to log")
    tr.log("run", f"complete · {len(scored)} findings · {len(all_failed)} analyzer error(s)")
    if job:
        job.status, job.finished_at, job.findings_count = "done", utcnow(), len(scored)
        tr.flush()
    return {"findings": len(scored), "digest": digest, "verdict": case_band, "graph": graph}


def findings_digest(scored: list[dict]) -> str:
    """Hash of everything a rerun must reproduce: IDs, locations, scores, ranges, bands."""
    canon = [{k: f[k] for k in ("finding_id", "evidence", "indicator", "location", "raw_score", "score", "lo", "hi", "band")}
             for f in scored]
    return custody.sha256_json(canon)


def _meta_label(ev: Evidence, meta: dict) -> str:
    from .ingest.service import meta_label

    return meta_label(ev.kind, ev.size, meta)

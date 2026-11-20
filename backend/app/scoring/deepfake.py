"""AI-generation assessment, kept separate from forensic editing indicators.

Editing is not evidence of AI generation. Use the learned detector once, with its
calibration/range; expose editing findings only as separate review context.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Optional

from .. import config

ASSESSMENT_VERSION = "ai-only-v5"
DEEPFAKE_MIN, DEEPFAKE_MIN_LO = 0.65, 0.50
AUTHENTIC_MAX, AUTHENTIC_MAX_HI = 0.35, 0.50
UNCALIBRATED_HALF = 0.20
P_MIN, P_MAX = 0.01, 0.99
VIDEO_EXTRA = 0.15
LABELS = {"deepfake": "Strong AI-generation signal", "authentic": "Low AI-generation signal", "uncertain": "AI-generation check inconclusive"}


@lru_cache(maxsize=1)
def _table() -> dict:
    p = config.VALIDATION_DIR / "results" / "deepfake_calibration.json"
    return json.loads(p.read_text()) if p.exists() else {}


def chosen_models(detector: str) -> list[str]:
    """Models validation selected for this detector (empty when not validated yet)."""
    return list(_table().get("detectors", {}).get(detector, {}).get("models", []))


def reload() -> None:
    _table.cache_clear()


def _sig(x: float) -> float:
    return 1 / (1 + math.exp(-max(-60, min(60, x))))


def calibrate(detector: str, raw: float) -> dict:
    """Detector raw score → calibrated P(AI-generated) with a bootstrap range."""
    entry = _table().get("detectors", {}).get(detector)
    raw = min(max(raw, 0.0), 1.0)
    if detector == "ai_video":
        return {"p": raw, "lo": 0.0, "hi": 1.0, "calibrated": False,
                "calibration_scope": "unvalidated-video", "diagnostic_only": True,
                "calibration_note": "Still-image frame scores are not calibrated video probabilities; compression and scene content can cause false alarms."}

    if not entry:
        return {"p": raw, "lo": max(0.0, raw - UNCALIBRATED_HALF), "hi": min(1.0, raw + UNCALIBRATED_HALF), "calibrated": False}
    p = min(max(_sig(entry["A"] * raw + entry["B"]), P_MIN), P_MAX)
    boots = sorted(_sig(a * raw + b) for a, b in entry.get("boot", [])) or [p]
    lo, hi = boots[int(0.1 * (len(boots) - 1))], boots[int(0.9 * (len(boots) - 1))]
    lo, hi = min(lo, p - 0.03), max(hi, p + 0.03)
    return {"p": p, "lo": max(P_MIN, lo), "hi": min(P_MAX, hi), "calibrated": True,
            "calibration_scope": "labelled-modality-sample",
            "calibration_note": "Calibrated on a small labelled sample; not proof of authenticity.",
            "auc": entry.get("auc"), "n": entry.get("n")}



VIDEO_MIN_FRAMES, VIDEO_MIN_AGREEMENT = 6, 0.8


def video_estimate(detector: dict) -> dict:
    """Experimental video estimate from sampled frames.

    Given only when the frames clearly agree (at least 80 % of at least 6 frames on the same side of 0.5): one odd
    frame from compression or a scene change cannot decide the clip. Uses the still-image calibration with a range
    widened by 0.15 because the detector has not been validated on labelled videos. Otherwise: no percentage."""
    frames = [float(f["p"]) for f in detector.get("frames") or []]
    n, high = len(frames), sum(p >= 0.5 for p in frames)
    agree = max(high, n - high) / n if n else 0.0
    if n < VIDEO_MIN_FRAMES or agree < VIDEO_MIN_AGREEMENT:
        return {"p": float(detector["raw"]), "lo": 0.0, "hi": 1.0, "calibrated": False, "diagnostic_only": True,
                "calibration_scope": "unvalidated-video", "frames_ai": high, "frames_n": n,
                "calibration_note": f"The sampled frames disagree ({high} of {n} look AI-generated), so no reliable "
                                    "video percentage can be given. Compression and scene changes can affect single frames."}
    base = calibrate("ai_image", float(detector["raw"]))
    return {**base, "lo": max(P_MIN, base["lo"] - VIDEO_EXTRA), "hi": min(P_MAX, base["hi"] + VIDEO_EXTRA),
            "experimental": True, "calibration_scope": "video-frames-experimental", "frames_ai": high, "frames_n": n,
            "calibration_note": f"Experimental video estimate: {high} of {n} sampled frames look AI-generated. Based on "
                                "the still-image detector's calibration with a wider range; not yet validated on labelled videos."}


def label(p: float, lo: float, hi: float) -> str:
    if p >= DEEPFAKE_MIN and lo >= DEEPFAKE_MIN_LO:
        return "deepfake"
    if p <= AUTHENTIC_MAX and hi <= AUTHENTIC_MAX_HI:
        return "authentic"
    return "uncertain"


def assess_item(detector: Optional[dict], manip: Optional[dict], kind: str, text_words: Optional[int] = None) -> dict:
    """Assess AI generation only; never promote editing traces into a deepfake probability."""
    ai = None
    if detector and detector.get("applicable") is False:
        return {"version": ASSESSMENT_VERSION, "p": None, "lo": None, "hi": None,
                "label": "uncertain", "text": LABELS["uncertain"], "ai": None, "manipulation": None,
                "calibrated": False, "not_applicable": True, "gate": detector.get("gate"),
                "why": f"Synthetic-speech check not applied: {detector.get('reason')}."}
    if detector and detector.get("raw") is not None and kind == "video":
        ai = video_estimate(detector)
    elif detector and detector.get("raw") is not None:
        name = {"image": "ai_image", "video": "ai_video", "audio": "ai_voice", "text": "ai_text"}[kind]
        ai = calibrate(name, detector["raw"])
        if kind == "text" and text_words is not None and text_words < 40:
            ai = {**ai, "lo": max(0.0, min(ai["p"] - 0.3, 0.45)),
                  "hi": min(1.0, max(ai["p"] + 0.3, 0.55)), "short_text": True,
                  "calibrated": False, "calibration_note": "Text shorter than 40 words has insufficient evidence for a reliable writing assessment."}
    m = None
    if manip and manip.get("findings") and kind != "text":
        m = {k: manip[k] for k in ("p", "lo", "hi")}
    if ai is None:
        return {"version": ASSESSMENT_VERSION, "p": None, "lo": None, "hi": None,
                "label": "uncertain", "text": LABELS["uncertain"],
                "why": "no AI-generation detector ran; editing indicators cannot establish AI generation",
                "ai": None, "manipulation": m, "calibrated": False}
    if (kind == "video" and ai.get("diagnostic_only")) or ai.get("short_text"):
        return {"version": ASSESSMENT_VERSION, "p": None, "lo": None, "hi": None,
                "label": "uncertain", "text": LABELS["uncertain"], "ai": ai,
                "manipulation": m, "calibrated": False, "diagnostic_only": True,
                "why": (ai.get("calibration_note") or "No reliable video estimate is available."
                        if kind == "video" else "Too little text for a reliable AI-writing assessment; at least 40 words are needed.")}
    clip = lambda x: min(max(x, P_MIN), P_MAX)
    p, lo, hi = (clip(ai[k]) for k in ("p", "lo", "hi"))
    lab = label(p, lo, hi)
    why = f"AI-generation detector {p:.0%}; editing indicators are assessed separately"
    return {"version": ASSESSMENT_VERSION, "p": round(p, 4), "lo": round(min(lo, p), 4),
            "hi": round(max(hi, p), 4), "label": lab, "text": LABELS[lab], "why": why,
            "ai": ai, "manipulation": m, "calibrated": ai.get("calibrated", False)}


def assess_case(items: dict[str, dict]) -> dict:
    """Show the highest AI-generation estimate and identify its evidence source."""
    scored = {k: v for k, v in items.items() if v.get("p") is not None}
    if not scored:
        return {"version": ASSESSMENT_VERSION, "p": None, "lo": None, "hi": None,
                "label": "uncertain", "text": LABELS["uncertain"],
                "why": "No reliable case probability is available. Review the individual evidence and analysis coverage.", "driver": None,
                "calibrated": False}
    key, top = max(scored.items(), key=lambda kv: (kv[1]["p"], kv[1]["lo"]))
    result = {**top, "driver": key, "why": f"{key}: {top['why']}"}
    missing = [k for k, v in items.items() if v.get("p") is None]
    uncertain = [k for k, v in items.items() if v.get("label") == "uncertain"]
    if top["label"] == "authentic" and (missing or uncertain):
        result.update(label="uncertain", text=LABELS["uncertain"])
        result["why"] += "; other evidence is unassessed or uncertain: " + ", ".join(sorted(set(missing + uncertain)))
    return result

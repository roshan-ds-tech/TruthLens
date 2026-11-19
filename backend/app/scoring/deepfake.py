"""Deepfake assessment: one calibrated probability per evidence item and per case, with a three-way verdict.

"Deepfake" here means the media is AI-generated *or* was manipulated. Two independent parts feed it:

  P_ai     the learned detector's score, Platt-calibrated on a labelled real-vs-AI sample
           (validation/results/deepfake_calibration.json); uncalibrated detectors get a wide ±0.2 range
  P_manip  the fused manipulation evidence for the same item (editing traces, see fuse.py), counted only when
           the item has at least one listed finding. Not used for text: a caption that contradicts other evidence
           is misleading, not AI-written, so for text only the AI-writing detector counts.

  P(deepfake) = 1 − (1 − P_ai)(1 − P_manip)          (the same formula on the low and high ends gives the range)
  P is kept within [0.01, 0.99]: no detector here justifies certainty.

Verdicts on the range:
  Likely deepfake    P ≥ 0.65 and low end ≥ 0.50
  Likely authentic   P ≤ 0.35 and high end ≤ 0.50
  Uncertain          anything else: the range crosses the middle, or the evidence is too thin
A case takes the assessment of its most likely deepfake item (and says which one).
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Optional

from .. import config

DEEPFAKE_MIN, DEEPFAKE_MIN_LO = 0.65, 0.50
AUTHENTIC_MAX, AUTHENTIC_MAX_HI = 0.35, 0.50
UNCALIBRATED_HALF = 0.20
P_MIN, P_MAX = 0.01, 0.99
VIDEO_EXTRA = 0.15
LABELS = {"deepfake": "Likely deepfake", "authentic": "Likely authentic", "uncertain": "Uncertain"}


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
    if not entry:
        return {"p": raw, "lo": max(0.0, raw - UNCALIBRATED_HALF), "hi": min(1.0, raw + UNCALIBRATED_HALF), "calibrated": False}
    p = min(max(_sig(entry["A"] * raw + entry["B"]), P_MIN), P_MAX)
    boots = sorted(_sig(a * raw + b) for a, b in entry.get("boot", [])) or [p]
    lo, hi = boots[int(0.1 * (len(boots) - 1))], boots[int(0.9 * (len(boots) - 1))]
    lo, hi = min(lo, p - 0.03), max(hi, p + 0.03)
    if detector == "ai_video":
        # calibrated on still images; compressed video frames are less reliable, so the range is wider
        lo, hi = lo - VIDEO_EXTRA, hi + VIDEO_EXTRA
    return {"p": p, "lo": max(P_MIN, lo), "hi": min(P_MAX, hi), "calibrated": True,
            "auc": entry.get("auc"), "n": entry.get("n")}


def label(p: float, lo: float, hi: float) -> str:
    if p >= DEEPFAKE_MIN and lo >= DEEPFAKE_MIN_LO:
        return "deepfake"
    if p <= AUTHENTIC_MAX and hi <= AUTHENTIC_MAX_HI:
        return "authentic"
    return "uncertain"


def assess_item(detector: Optional[dict], manip: Optional[dict], kind: str, text_words: Optional[int] = None) -> dict:
    """Combine the learned detector (if it ran) and the manipulation evidence (if any) for one item."""
    parts, reasons = [], []
    ai = None
    if detector and detector.get("raw") is not None:
        name = {"image": "ai_image", "video": "ai_video", "audio": "ai_voice", "text": "ai_text"}[detector["kind"]]
        ai = calibrate(name, detector["raw"])
        if kind == "text" and text_words is not None and text_words < 40:
            # too little text for the classifier: the range always spans 45–55 %, so on its own it can never give
            # a confident answer either way
            ai = {**ai, "lo": max(0.0, min(ai["p"] - 0.3, 0.45)), "hi": min(1.0, max(ai["p"] + 0.3, 0.55)), "short_text": True}
        parts.append(ai)
        reasons.append(f"AI-generation detector {ai['p']:.0%}")
    m = None
    if manip and manip.get("findings") and kind != "text":
        m = {"p": manip["p"], "lo": manip["lo"], "hi": manip["hi"]}
        parts.append(m)
        reasons.append(f"manipulation evidence {m['p']:.0%}")
    if not parts:
        return {"p": None, "lo": None, "hi": None, "label": "uncertain", "text": LABELS["uncertain"],
                "why": "no deepfake detector ran on this item and no manipulation evidence was found",
                "ai": None, "manipulation": None, "calibrated": False}

    def combine(key: str) -> float:
        prod = 1.0
        for x in parts:
            prod *= 1 - x[key]
        return 1 - prod

    clip = lambda x: min(max(x, P_MIN), P_MAX)  # noqa: E731
    p, lo, hi = clip(combine("p")), clip(combine("lo")), clip(combine("hi"))
    lab = label(p, lo, hi)
    return {"p": round(p, 4), "lo": round(min(lo, p), 4), "hi": round(max(hi, p), 4), "label": lab, "text": LABELS[lab],
            "why": " and ".join(reasons), "ai": ai, "manipulation": m,
            "calibrated": bool(ai and ai.get("calibrated")) or ai is None}


def assess_case(items: dict[str, dict]) -> dict:
    """The case is as likely a deepfake as its most likely item."""
    scored = {k: v for k, v in items.items() if v.get("p") is not None}
    if not scored:
        return {"p": None, "lo": None, "hi": None, "label": "uncertain", "text": LABELS["uncertain"],
                "why": "no item could be assessed", "driver": None}
    key, top = max(scored.items(), key=lambda kv: (kv[1]["p"], kv[1]["lo"]))
    return {**{k: top[k] for k in ("p", "lo", "hi", "label", "text")}, "driver": key,
            "why": f"{key}: {top['why']}", "calibrated": top.get("calibrated", False)}

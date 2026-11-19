"""Prosody statistics (§3.5): pitch jitter / variability and pause-length spread.

Unusually uniform values are reported as a weak indicator only; many real speakers are monotone.
"""
from __future__ import annotations

import numpy as np

from ..base import AnalysisContext, RawFinding
from .common import frame_rms_db, load_16k

MIN_VOICED_FRAMES = 120
ALTERNATIVES = ["A naturally monotone speaker or a read-out statement", "Heavy noise suppression flattening the voice"]


def stats(y: np.ndarray, sr: int) -> dict | None:
    import librosa

    y = y[: sr * 60]   # pyin is the slowest step; one minute is enough for these statistics
    f0, voiced, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr, frame_length=1024, hop_length=256)
    f0v = f0[voiced & ~np.isnan(f0)]
    if len(f0v) < MIN_VOICED_FRAMES:
        return None
    jitter = float(np.mean(np.abs(np.diff(f0v))) / np.mean(f0v))
    cv = float(np.std(f0v) / np.mean(f0v))
    db, _ = frame_rms_db(y, sr, 0.02, 0.01)
    quiet = db < (np.percentile(db, 10) + 6)
    runs, n = [], 0
    for q in quiet:
        if q:
            n += 1
        elif n:
            runs.append(n)
            n = 0
    pauses = np.array([r * 0.01 for r in runs if r >= 15])   # pauses ≥ 150 ms
    pause_cv = float(np.std(pauses) / np.mean(pauses)) if len(pauses) >= 4 else None
    return {"f0_mean_hz": round(float(np.mean(f0v)), 1), "f0_cv": round(cv, 4), "jitter": round(jitter, 4),
            "pauses": int(len(pauses)), "pause_cv": None if pause_cv is None else round(pause_cv, 3)}


def run(ctx: AnalysisContext) -> list[RawFinding]:
    y, sr = load_16k(ctx)
    s = stats(y, sr)
    ctx.extra["prosody"] = s or {"note": "too little voiced speech"}
    if not s:
        return []
    uniform_pitch = s["f0_cv"] < 0.08
    uniform_pauses = s["pause_cv"] is not None and s["pause_cv"] < 0.25
    if not (uniform_pitch and uniform_pauses):
        return []
    return [RawFinding(
        indicator="uniform_prosody", family="prosody", name="Unusually uniform pitch and pauses",
        location={"type": "time_range", "start": 0.0, "end": round(min(len(y) / sr, 60), 2)},
        loc_label=f"Whole track · pitch CV {s['f0_cv']:.3f} · pause CV {s['pause_cv']:.2f}",
        raw_score=0.42,
        method=f"librosa pYIN pitch: mean {s['f0_mean_hz']} Hz, coefficient of variation {s['f0_cv']:.3f} (< 0.08); "
               f"{s['pauses']} pauses ≥ 150 ms with CV {s['pause_cv']:.2f} (< 0.25)",
        explanation="Pitch varies very little and pauses are nearly the same length. Synthetic speech is often this even, "
                    "but this is a weak signal on its own.",
        alternatives=ALTERNATIVES, sort=0.0, extra=s)]

"""Coarse lip-sync measurement (§3.7, rule R-07): audio RMS envelope vs MediaPipe mouth opening.

Produces cross-modal findings (F-XM-*) for windows where speech energy and mouth movement stop
correlating although both a face and speech are present.
"""
from __future__ import annotations

import numpy as np

from ..analyzers.audio.common import load_16k
from ..analyzers.base import AnalysisContext, RawFinding, fmt_t, squash

WINDOW_S = 4.0
STEP_S = 1.0


def _envelope(y: np.ndarray, sr: int, times: np.ndarray) -> np.ndarray:
    half = int(0.06 * sr)
    out = []
    for t in times:
        c = int(t * sr)
        seg = y[max(0, c - half): c + half]
        out.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    return np.array(out)


def measure(video: AnalysisContext, audio: AnalysisContext, mouth: list[tuple[float, float]]) -> list[dict]:
    if len(mouth) < 16:
        return []
    t = np.array([m[0] for m in mouth])
    mo = np.array([m[1] for m in mouth])
    y, sr = load_16k(audio)
    env = _envelope(y, sr, t)
    speech_floor = np.percentile(env, 30) * 1.5 + 1e-4
    rows = []
    for start in np.arange(0, max(t[-1] - WINDOW_S, 0) + 1e-6, STEP_S):
        sel = (t >= start) & (t < start + WINDOW_S)
        if sel.sum() < 12 or (env[sel] > speech_floor).mean() < 0.4 or np.std(mo[sel]) < 1e-4 or np.std(env[sel]) < 1e-6:
            continue
        r = float(np.corrcoef(mo[sel], env[sel])[0, 1])
        rows.append({"start": round(float(start), 2), "end": round(float(start + WINDOW_S), 2), "r": round(r, 3)})
    return rows


def findings(video: AnalysisContext, audio: AnalysisContext, mouth: list[tuple[float, float]]) -> list[RawFinding]:
    rows = measure(video, audio, mouth)
    video.extra["lipsync"] = rows
    if len(rows) < 3:
        return []
    med = float(np.median([r["r"] for r in rows]))
    low = [r for r in rows if r["r"] < min(0.15, med - 0.3)]
    out: list[RawFinding] = []
    # merge overlapping low windows into segments
    segs: list[dict] = []
    for r in low:
        if segs and r["start"] <= segs[-1]["end"]:
            segs[-1]["end"] = r["end"]
            segs[-1]["min_r"] = min(segs[-1]["min_r"], r["r"])
        else:
            segs.append({"start": r["start"], "end": r["end"], "min_r": r["r"]})
    for s in segs:
        gap = med - s["min_r"]
        out.append(RawFinding(
            indicator="lipsync_weak", family="lipsync", name="Lip-sync weak correlation",
            location={"type": "time_range", "start": s["start"], "end": s["end"]},
            loc_label=f"{fmt_t(s['start'])}–{fmt_t(s['end'])}",
            raw_score=squash(gap, mid=0.6, scale=0.15),
            method=f"Pearson r between MediaPipe mouth opening ({video.label}) and speech RMS envelope ({audio.label}) in "
                   f"{WINDOW_S:g} s windows: {s['min_r']:.2f} here vs {med:.2f} median for this clip",
            explanation=f"Between {fmt_t(s['start'])} and {fmt_t(s['end'])} mouth movement and speech energy correlate weakly "
                        f"(r = {s['min_r']:.2f}, the rest of the clip {med:.2f}). Dubbed or cloned speech often drifts from the lips.",
            alternatives=["Head turned away from the camera", "Low mouth-region resolution", "Background speech from another person"],
            sort=s["start"], extra={"min_r": s["min_r"], "median_r": round(med, 3), "video": video.label, "audio": audio.label}))
    return out

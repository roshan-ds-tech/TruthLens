"""Splice points from noise-floor steps (§3.5).

The noise floor is the 10th percentile of 20 ms frame RMS in a window. A splice joins two recordings
with different background noise, so the floor steps and the spectrum of the quietest frames changes.
A pause in speech changes neither, which keeps speech onsets from being flagged.
"""
from __future__ import annotations

import numpy as np

from ... import config
from ..base import AnalysisContext, RawFinding, fmt_t, squash
from .common import frame_rms_db, load_16k, render_spectrogram, waveform_peaks

SIDE_S = 2.5       # window each side of a candidate boundary
GUARD_S = 0.15
NMS_S = 3.0
ALTERNATIVES = ["Microphone gain changed by an operator", "Noise suppression switching on or off",
                "A loud background source (fan, traffic) starting or stopping"]


def _quiet_spectrum(y: np.ndarray, sr: int, t0: float, t1: float) -> np.ndarray | None:
    seg = y[max(0, int(t0 * sr)): int(t1 * sr)]
    n = 512
    if len(seg) < n * 4:
        return None
    frames = np.lib.stride_tricks.sliding_window_view(seg, n)[::n // 2] * np.hanning(n)
    energy = (frames ** 2).mean(axis=1)
    quiet = frames[energy <= np.percentile(energy, 15)]
    spec = np.log10(np.abs(np.fft.rfft(quiet, axis=1)).mean(axis=0) + 1e-7)
    return spec - spec.mean()


PERSIST_S = 4.0


def _persistent(db: np.ndarray, times: np.ndarray, t: float, step: float) -> bool:
    """A splice changes the background for good: even the quietest frame on the louder side stays above
    the quietest frame on the quieter side. Dense speech only *looks* louder, since somewhere in it is a
    pause back at the old floor, so it fails this test."""
    before = db[(times >= t - PERSIST_S) & (times < t - GUARD_S)]
    after = db[(times > t + GUARD_S) & (times <= t + PERSIST_S)]
    if len(before) < 50 or len(after) < 50:
        return False
    low_b, low_a = np.percentile(before, 1), np.percentile(after, 1)
    gap = (low_a - low_b) if step > 0 else (low_b - low_a)
    return gap >= config.NOISE_FLOOR_STEP_DB * 0.75


def _refine(db: np.ndarray, times: np.ndarray, t: float, step: float) -> float:
    """Robust change point of a rolling-minimum floor trace (quietest 20 ms frame per 0.5 s).

    The fit minimises absolute deviation from each side's median, so a long syllable that keeps the
    window loud does not drag the boundary. A rolling minimum stays low until its window has fully left
    the quiet side, so the result is shifted back half a window when the floor rises (forward if it drops)."""
    near = (times > t - 2.0) & (times < t + 2.0)
    tt, dd = times[near], db[near]
    k = 50
    if len(dd) < 3 * k:
        return t
    trace = np.array([dd[max(0, i - k // 2): i + k // 2 + 1].min() for i in range(len(dd))])
    best, best_i = np.inf, None
    for i in range(k // 2, len(trace) - k // 2, 2):
        left, right = trace[:i], trace[i:]
        cost = np.abs(left - np.median(left)).sum() + np.abs(right - np.median(right)).sum()
        if cost < best:
            best, best_i = cost, i
    if best_i is None:
        return t
    half = (k // 2) * float(np.median(np.diff(tt)))
    return float(tt[best_i] - half if step > 0 else tt[best_i] + half)


def splice_candidates(y: np.ndarray, sr: int) -> list[dict]:
    db, times = frame_rms_db(y, sr, config.NOISE_FLOOR_FRAME_S, 0.01)
    if len(db) < 50:
        return []
    duration = len(y) / sr
    steps = []
    for t in np.arange(SIDE_S, duration - SIDE_S, 0.05):
        before = db[(times >= t - SIDE_S) & (times < t - GUARD_S)]
        after = db[(times > t + GUARD_S) & (times <= t + SIDE_S)]
        if len(before) < 20 or len(after) < 20:
            continue
        steps.append((t, float(np.percentile(after, 10) - np.percentile(before, 10))))
    if not steps:
        return []
    arr = np.array(steps)
    out: list[dict] = []
    order = np.argsort(-np.abs(arr[:, 1]), kind="stable")
    for i in order:
        t, step = arr[i]
        if abs(step) < config.NOISE_FLOOR_STEP_DB:
            break
        if any(abs(t - c["t"]) < NMS_S for c in out):
            continue
        if not _persistent(db, times, float(t), float(step)):
            continue
        sb, sa = _quiet_spectrum(y, sr, t - SIDE_S, t - GUARD_S), _quiet_spectrum(y, sr, t + GUARD_S, t + SIDE_S)
        spec_dist = float(np.sqrt(np.mean((sa - sb) ** 2))) if sb is not None and sa is not None else 0.0
        t = _refine(db, times, float(t), step)
        out.append({"t": round(float(t), 2), "step_db": round(float(step), 1), "spec_dist": round(spec_dist, 3)})
    return sorted(out, key=lambda c: c["t"])


def run(ctx: AnalysisContext) -> list[RawFinding]:
    y, sr = load_16k(ctx)
    ctx.extra["waveform"] = {"peaks": waveform_peaks(y), "duration": round(len(y) / sr, 3), "sr": sr}
    render_spectrogram(y, sr, ctx.artifact("spectrogram.png"))
    findings = []
    for c in splice_candidates(y, sr):
        strength = abs(c["step_db"]) / config.NOISE_FLOOR_STEP_DB + 4.0 * c["spec_dist"]
        direction = "rises" if c["step_db"] > 0 else "drops"
        findings.append(RawFinding(
            indicator="noise_floor_step", family="noise_floor", name="Noise-floor step (possible splice)",
            location={"type": "time_range", "start": c["t"], "end": round(c["t"] + 0.5, 2)},
            loc_label=f"{fmt_t(c['t'])} · {c['step_db']:+.0f} dB jump",
            raw_score=squash(strength, mid=2.4, scale=0.5),
            method=f"10th-percentile RMS of 20 ms frames, {SIDE_S:g} s each side: step {c['step_db']:+.1f} dB "
                   f"(threshold {config.NOISE_FLOOR_STEP_DB:g} dB); quiet-frame spectrum distance {c['spec_dist']:.2f}",
            explanation=f"Background noise {direction} by {abs(c['step_db']):.0f} dB at {fmt_t(c['t'])}, and the spectrum of the "
                        f"quietest frames changes at the same point. Two recordings joined together usually have different room noise.",
            alternatives=ALTERNATIVES, artifacts=["spectrogram.png"], sort=c["t"], extra=c))
    return findings

"""Temporal jumps (§3.4): Farneback optical-flow magnitude per frame; robust z-score spikes = possible cut.

A spike inside one continuous shot (similar histograms either side) is reported as a discontinuity.
A spike with a scene change is an ordinary edit cut and is only recorded as a note.
"""
from __future__ import annotations

import cv2
import numpy as np

from ... import config
from ..base import AnalysisContext, RawFinding, fmt_t, squash
from .frames import decode

LOCAL_S = 2.0
SHOT_CHANGE_NCC = 0.5    # frame-to-frame correlation below this = a new shot
ISOLATION = 0.35         # a neighbouring frame may reach at most this share of the spike's z
MIN_JUMP_RATIO = 3.0     # motion at the jump vs the median of the 3 frames each side


def frame_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Normalised cross-correlation of two small greyscale frames (1 = same picture, ~0 = different shot)."""
    a = cv2.resize(a, (64, 36), interpolation=cv2.INTER_AREA).astype(np.float64).ravel()
    b = cv2.resize(b, (64, 36), interpolation=cv2.INTER_AREA).astype(np.float64).ravel()
    a -= a.mean()
    b -= b.mean()
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def aligned_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Similarity after undoing a pure camera shift (phase correlation). A camera that jumped along its path
    still shares picture content with the previous frame once shifted back; a new shot does not."""
    a32, b32 = a.astype(np.float32), b.astype(np.float32)
    (dx, dy), _ = cv2.phaseCorrelate(a32, b32)
    h, w = a.shape
    ix, iy = -int(round(dx)), -int(round(dy))   # phaseCorrelate reports b's shift relative to a; undo it
    if abs(ix) >= w * 0.8 or abs(iy) >= h * 0.8:
        return frame_similarity(a, b)
    xa, xb = (max(0, ix), max(0, -ix))
    ya, yb = (max(0, iy), max(0, -iy))
    ow, oh = w - abs(ix), h - abs(iy)
    return frame_similarity(a[ya:ya + oh, xa:xa + ow], b[yb:yb + oh, xb:xb + ow])


def flow_series(gray: list[np.ndarray]) -> np.ndarray:
    mags = [0.0]
    for i in range(1, len(gray)):
        flow = cv2.calcOpticalFlowFarneback(gray[i - 1], gray[i], None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mags.append(float(np.mean(np.hypot(flow[..., 0], flow[..., 1]))))
    return np.array(mags)


def local_z(series: np.ndarray, t: np.ndarray) -> np.ndarray:
    """z against a rolling ±2 s median/MAD, so a pan does not hide a spike and a still shot does not invent one."""
    z = np.zeros_like(series)
    for i in range(len(series)):
        win = series[(t >= t[i] - LOCAL_S) & (t <= t[i] + LOCAL_S)]
        win = np.delete(win, np.argmin(np.abs(win - series[i]))) if len(win) > 3 else win
        med = np.median(win)
        mad = max(np.median(np.abs(win - med)) * 1.4826, 0.05 + 0.1 * med)
        z[i] = (series[i] - med) / mad
    return z


def run(ctx: AnalysisContext) -> list[RawFinding]:
    fr = decode(ctx)
    t, gray, hist = fr["t"], fr["gray"], fr["hist"]
    mags = flow_series(gray)
    diffs = fr.get("diffs")
    z = local_z(mags, t)
    zd = local_z(diffs, t) if diffs is not None else np.zeros_like(z)
    fr["flow_z"] = np.maximum(z, zd)
    findings, cuts = [], []
    last = -10.0
    order = np.argsort(-fr["flow_z"], kind="stable")
    picked: list[int] = []
    for i in order:
        if fr["flow_z"][i] < config.FLOW_Z:
            break
        # A boundary has no baseline on both sides. Decoder startup motion is not a splice.
        if i < 4 or i >= len(gray) - 3:
            continue
        if any(abs(t[i] - t[j]) < 1.0 for j in picked):
            continue
        picked.append(int(i))
    z_all = fr["flow_z"]
    natural = 0
    for i in sorted(picked):
        same_shot = float(cv2.compareHist(hist[i - 1].astype(np.float32), hist[i].astype(np.float32), cv2.HISTCMP_CORREL))
        if same_shot < 0.6 or max(frame_similarity(gray[i - 1], gray[i]), aligned_similarity(gray[i - 1], gray[i])) < SHOT_CHANGE_NCC:
            cuts.append(float(t[i]))      # a new shot: ordinary editing, recorded as a note
            continue
        # A cut inside a shot is one isolated jump; people moving or a hand-held camera ramp over several frames.
        nb = [z_all[k] for k in (i - 1, i + 1) if 0 <= k < len(z_all)]
        def jump_ratio(series: np.ndarray) -> float:
            around = np.concatenate([series[max(1, i - 3):i], series[i + 1:i + 4]])
            return float(series[i] / max(np.median(around), 0.05)) if len(around) else 0.0
        # optical flow loses track of very large jumps, so the pixel-difference jump counts as well
        ratio = max(jump_ratio(mags), jump_ratio(diffs) if diffs is not None else 0.0)
        if (nb and max(nb) > ISOLATION * z_all[i]) or ratio < MIN_JUMP_RATIO:
            natural += 1
            continue
        zz = float(fr["flow_z"][i])
        findings.append(RawFinding(
            indicator="flow_discontinuity", family="optical_flow", name="Optical-flow discontinuity",
            location={"type": "frame_range", "start": float(t[i - 1]), "end": float(t[i]), "frames": [int(i - 1), int(i)]},
            loc_label=f"{fmt_t(t[i])} · frames {i - 1}–{i}",
            raw_score=squash(zz, mid=config.FLOW_Z + 3.0, scale=1.5),
            method=f"Farneback optical flow on {config.VIDEO_WORK_WIDTH}px frames: motion {mags[i]:.2f} px vs local median; "
                   f"robust z {zz:.1f} (threshold {config.FLOW_Z:g}), {ratio:.1f}× neighbouring motion, isolated single-frame jump; "
                   f"frame similarity {frame_similarity(gray[i - 1], gray[i]):.2f} (same shot)",
            explanation=f"Motion jumps at {fmt_t(t[i])} in a single frame, {ratio:.0f}× the surrounding motion, inside what is otherwise "
                        f"one continuous shot. "
                        f"This pattern is consistent with a cut or an inserted segment.",
            alternatives=["Dropped frames during screen recording", "Variable frame-rate re-encode by the uploading app",
                          "Sudden camera shake"],
            sort=float(t[i]), extra={"z": round(zz, 2), "hist_corr": round(same_shot, 3), "jump_ratio": round(ratio, 2)}))
        last = t[i]
    ctx.extra["cuts"] = cuts
    ctx.log("video", f"optical flow: {len(findings)} discontinuit{'y' if len(findings) == 1 else 'ies'}, {len(cuts)} scene cut(s), "
                     f"{natural} gradual motion peak(s) ignored")
    return findings

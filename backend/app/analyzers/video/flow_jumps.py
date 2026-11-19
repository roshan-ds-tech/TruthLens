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
        if fr["flow_z"][i] < config.FLOW_Z or i < 1:
            break
        if any(abs(t[i] - t[j]) < 1.0 for j in picked):
            continue
        picked.append(int(i))
    for i in sorted(picked):
        same_shot = float(cv2.compareHist(hist[i - 1].astype(np.float32), hist[i].astype(np.float32), cv2.HISTCMP_CORREL))
        if same_shot < 0.6:
            cuts.append(float(t[i]))
            continue
        zz = float(fr["flow_z"][i])
        findings.append(RawFinding(
            indicator="flow_discontinuity", family="optical_flow", name="Optical-flow discontinuity",
            location={"type": "frame_range", "start": float(t[i - 1]), "end": float(t[i]), "frames": [int(i - 1), int(i)]},
            loc_label=f"{fmt_t(t[i])} · frames {i - 1}–{i}",
            raw_score=squash(zz, mid=config.FLOW_Z + 3.0, scale=1.5),
            method=f"Farneback optical flow on {config.VIDEO_WORK_WIDTH}px frames: motion {mags[i]:.2f} px vs local median; "
                   f"robust z {zz:.1f} (threshold {config.FLOW_Z:g}); histogram correlation {same_shot:.2f} (same shot)",
            explanation=f"Motion jumps at {fmt_t(t[i])} inside what is otherwise one continuous shot. "
                        f"This pattern is consistent with a cut or an inserted segment.",
            alternatives=["Dropped frames during screen recording", "Variable frame-rate re-encode by the uploading app",
                          "Sudden camera shake"],
            sort=float(t[i]), extra={"z": round(zz, 2), "hist_corr": round(same_shot, 3)}))
        last = t[i]
    ctx.extra["cuts"] = cuts
    ctx.log("video", f"optical flow: {len(findings)} discontinuit{'y' if len(findings) == 1 else 'ies'}, {len(cuts)} scene cut(s)")
    return findings

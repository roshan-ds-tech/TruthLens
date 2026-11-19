"""Frame decoding (§3.4). Frames are decoded once per evidence item and kept small in memory.

Everything here is held in ``ctx.extra`` under keys starting with ``_`` (transient, never persisted).
"""
from __future__ import annotations

import cv2
import numpy as np

from ... import config
from ..base import AnalysisContext, RawFinding


def decode(ctx: AnalysisContext) -> dict:
    if "_frames" in ctx.extra:
        return ctx.extra["_frames"]
    cap = cv2.VideoCapture(str(ctx.original))
    if not cap.isOpened():
        raise RuntimeError("OpenCV could not open the video")
    fps = cap.get(cv2.CAP_PROP_FPS) or ctx.metadata.get("fps") or 25.0
    small, times, hists = [], [], []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if t <= 0 and idx > 0:
            t = idx / fps
        if t > config.MAX_VIDEO_SECONDS:
            break
        h, w = frame.shape[:2]
        sw = config.VIDEO_WORK_WIDTH
        g = cv2.cvtColor(cv2.resize(frame, (sw, max(2, int(h * sw / w))), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        small.append(g)
        times.append(round(t, 4))
        hist = cv2.calcHist([g], [0], None, [32], [0, 256])
        hists.append(cv2.normalize(hist, hist).ravel())
        idx += 1
    cap.release()
    if len(small) < 3:
        raise RuntimeError("video has fewer than 3 decodable frames")
    out = {"gray": small, "t": np.array(times), "hist": np.array(hists), "fps": float(fps),
           "width": ctx.metadata.get("width"), "height": ctx.metadata.get("height")}
    ctx.extra["_frames"] = out
    return out


def read_frame(ctx: AnalysisContext, index: int) -> np.ndarray | None:
    """Full-resolution RGB frame (downscaled to ≤ 720p), for the image pipeline on suspicious frames."""
    cap = cv2.VideoCapture(str(ctx.original))
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return None
    h, w = frame.shape[:2]
    if h > config.MAX_VIDEO_HEIGHT:
        frame = cv2.resize(frame, (int(w * config.MAX_VIDEO_HEIGHT / h), config.MAX_VIDEO_HEIGHT), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def run(ctx: AnalysisContext) -> list[RawFinding]:
    fr = decode(ctx)
    ctx.log("video", f"decoded {len(fr['gray'])} frames · {fr['fps']:.2f} fps · work width {config.VIDEO_WORK_WIDTH}px")
    return []

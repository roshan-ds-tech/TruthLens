"""Duplicate and dropped frames (§3.4).

Duplicate: a frame identical to its neighbour (zero perceptual-hash distance, near-zero pixel change)
while the frames around it are moving. Drop: a gap in timestamps larger than the normal frame interval.
"""
from __future__ import annotations

import imagehash
import numpy as np
from PIL import Image

from ..base import AnalysisContext, RawFinding, fmt_t, squash
from .frames import decode

MOTION = 1.5        # mean absolute grey change that counts as "moving"
STILL = 0.25


def frame_diffs(gray: list[np.ndarray]) -> np.ndarray:
    d = [0.0] + [float(np.mean(np.abs(gray[i].astype(np.int16) - gray[i - 1].astype(np.int16)))) for i in range(1, len(gray))]
    return np.array(d)


def run(ctx: AnalysisContext) -> list[RawFinding]:
    fr = decode(ctx)
    gray, t = fr["gray"], fr["t"]
    diffs = frame_diffs(gray)
    fr["diffs"] = diffs
    hashes = [imagehash.phash(Image.fromarray(g)) for g in gray]
    dupes = []
    for i in range(2, len(gray) - 1):
        if hashes[i] - hashes[i - 1] == 0 and diffs[i] < STILL and diffs[i - 1] > MOTION and diffs[i + 1] > MOTION:
            dupes.append(i)
    dt = np.diff(t)
    med = float(np.median(dt)) if len(dt) else 0.0
    drops = [(i + 1, int(round(g / med)) - 1) for i, g in enumerate(dt) if med > 0 and g > 1.8 * med]
    fr["events"] = {"dupes": dupes, "drops": [d[0] for d in drops]}
    findings: list[RawFinding] = []
    for group in _group(dupes, 3):
        a, b = group[0], group[-1]
        motion = float(np.mean([diffs[a - 1], diffs[min(b + 1, len(diffs) - 1)]]))
        findings.append(RawFinding(
            indicator="duplicate_frames", family="frame_dupes", name="Duplicated frame inside motion",
            location={"type": "frame_range", "start": float(t[a]), "end": float(t[b]) + med, "frames": [int(a), int(b)]},
            loc_label=f"{fmt_t(t[a])} · frame{'s' if b > a else ''} {a}{'–' + str(b) if b > a else ''}",
            raw_score=squash(len(group) + motion / 4, mid=2.0, scale=0.8),
            method=f"pHash distance 0 to the previous frame, mean pixel change {diffs[a]:.2f} while neighbours move {motion:.1f} grey levels",
            explanation=f"Frame {a} repeats the previous frame exactly while the scene around it is moving. "
                        f"Repeated frames appear where footage was cut and padded to keep its length.",
            alternatives=["Variable frame-rate re-encode by the uploading app", "Dropped frames during screen recording"],
            sort=float(t[a]), extra={"frames": group}))
    for i, missing in drops:
        findings.append(RawFinding(
            indicator="dropped_frames", family="frame_dupes", name="Timestamp gap (dropped frames)",
            location={"type": "frame_range", "start": float(t[i - 1]), "end": float(t[i]), "frames": [int(i - 1), int(i)]},
            loc_label=f"{fmt_t(t[i - 1])} · ~{missing} frame{'s' if missing > 1 else ''} missing",
            raw_score=squash(missing, mid=2.0, scale=1.0),
            method=f"Frame timestamps jump by {t[i] - t[i - 1]:.3f} s against a median interval of {med:.3f} s",
            explanation=f"About {missing} frame{'s are' if missing > 1 else ' is'} missing at {fmt_t(t[i - 1])}. "
                        f"Gaps appear where a segment was removed without re-timing.",
            alternatives=["Variable frame-rate recording on a phone", "Network stream recorded with packet loss"],
            sort=float(t[i - 1])))
    ctx.log("video", f"pHash: {len(dupes)} duplicate frame(s), {len(drops)} timestamp gap(s)")
    return findings


def _group(idx: list[int], gap: int) -> list[list[int]]:
    groups: list[list[int]] = []
    for i in idx:
        if groups and i - groups[-1][-1] <= gap:
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups

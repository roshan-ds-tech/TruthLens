"""Copy-move detection (§3.3): ORB keypoints matched within the same image, RANSAC affine, inlier clusters."""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageDraw

from ... import config
from ..base import AnalysisContext, RawFinding, squash
from .common import HEATMAP_MAX_SIDE, Region, describe_position, load_rgb

MAX_SIDE = 1200
ALTERNATIVES = ["Repeating natural or printed texture (tiles, foliage, logos on a banner)",
                "Symmetric objects photographed head-on"]


def find_clones(gray: np.ndarray) -> list[dict]:
    orb = cv2.ORB_create(nfeatures=config.COPYMOVE_MAX_FEATURES, fastThreshold=10)
    kps, des = orb.detectAndCompute(gray, None)
    if des is None or len(kps) < 30:
        return []
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    knn = matcher.knnMatch(des, des, k=3)
    src, dst = [], []
    seen = set()
    for ms in knn:
        cand = [m for m in ms if m.trainIdx != m.queryIdx]
        if len(cand) < 2 or cand[0].distance > 64 or cand[0].distance > 0.75 * cand[1].distance:
            continue
        m = cand[0]
        p, q = np.array(kps[m.queryIdx].pt), np.array(kps[m.trainIdx].pt)
        if np.linalg.norm(p - q) < config.COPYMOVE_MIN_DIST:
            continue
        key = (min(m.queryIdx, m.trainIdx), max(m.queryIdx, m.trainIdx))
        if key in seen:
            continue
        seen.add(key)
        if (p[0], p[1]) > (q[0], q[1]):   # canonical direction so a→b and b→a fit one transform
            p, q = q, p
        src.append(p)
        dst.append(q)
    clusters = []
    src_a, dst_a = np.float32(src), np.float32(dst)
    cv2.setRNGSeed(config.SEED)
    for _ in range(2):
        if len(src_a) < config.COPYMOVE_MIN_INLIERS:
            break
        M, inl = cv2.estimateAffinePartial2D(src_a, dst_a, method=cv2.RANSAC, ransacReprojThreshold=3.0,
                                             maxIters=4000, confidence=0.995)
        if M is None or inl is None:
            break
        inl = inl.ravel().astype(bool)
        n = int(inl.sum())
        shift = float(np.hypot(M[0, 2], M[1, 2]))
        if n >= config.COPYMOVE_MIN_INLIERS and shift >= config.COPYMOVE_MIN_DIST:
            clusters.append({"src": src_a[inl], "dst": dst_a[inl], "inliers": n, "M": M})
        src_a, dst_a = src_a[~inl], dst_a[~inl]
    return clusters


def _box(pts: np.ndarray, scale: float, w: int, h: int, pad: int = 16) -> Region:
    x0, y0 = pts.min(axis=0) / scale - pad
    x1, y1 = pts.max(axis=0) / scale + pad
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    return Region(x=x0, y=y0, w=min(w - x0, int(x1) - x0), h=min(h - y0, int(y1) - y0), mean_z=0, peak_z=0, area_fraction=0)


def run(ctx: AnalysisContext) -> list[RawFinding]:
    rgb = load_rgb(ctx.original)
    h, w = rgb.shape[:2]
    scale = min(1.0, MAX_SIDE / max(h, w))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    if scale < 1:
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    clusters = find_clones(gray)
    ov_scale = min(1.0, HEATMAP_MAX_SIDE / max(w, h))
    overlay = Image.new("RGBA", (max(1, int(w * ov_scale)), max(1, int(h * ov_scale))), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    findings = []
    for i, cl in enumerate(clusters):
        a, b = _box(cl["src"], scale, w, h), _box(cl["dst"], scale, w, h)
        for box, tag in ((a, "A"), (b, "A′")):
            draw.rectangle([box.x * ov_scale, box.y * ov_scale, (box.x + box.w) * ov_scale, (box.y + box.h) * ov_scale],
                           outline=(255, 255, 255, 255), width=2)
            draw.text((box.x * ov_scale + 4, box.y * ov_scale + 2), tag if i == 0 else tag.replace("A", "B"),
                      fill=(255, 255, 255, 255))
        for p, q in list(zip(cl["src"], cl["dst"]))[:40]:
            draw.line([p[0] / scale * ov_scale, p[1] / scale * ov_scale, q[0] / scale * ov_scale, q[1] / scale * ov_scale],
                      fill=(255, 210, 63, 150), width=1)
        where = describe_position(b, w, h)
        findings.append(RawFinding(
            indicator="copy_move", family="copy_move", name="Copy-move match",
            location={"type": "bbox", "x": b.x, "y": b.y, "w": b.w, "h": b.h, "image_w": w, "image_h": h,
                      "pair": {"x": a.x, "y": a.y, "w": a.w, "h": a.h}},
            loc_label=f"{where.capitalize()} region ↔ ({a.x}, {a.y})",
            raw_score=squash(cl["inliers"], mid=22.0, scale=6.0),
            method=f"ORB keypoints matched within the image, distance > {config.COPYMOVE_MIN_DIST}px, "
                   f"RANSAC similarity transform: {cl['inliers']} inliers",
            explanation=f"The {where} region at ({b.x}, {b.y}) matches the area at ({a.x}, {a.y}) through one consistent "
                        f"shift, with {cl['inliers']} keypoints agreeing. Duplicating part of an image to hide or add content leaves this pattern.",
            alternatives=ALTERNATIVES, artifacts=["copymove.png"], sort=b.y + b.x / 1e5,
            extra={"inliers": cl["inliers"]}))
    overlay.save(ctx.artifact("copymove.png"))
    return findings

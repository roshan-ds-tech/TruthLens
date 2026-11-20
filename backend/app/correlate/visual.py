"""Verify image/video region correspondence before R-09 may corroborate findings.

Equal normalized coordinates in unrelated pictures are not visual evidence. Register
features with a RANSAC homography, then compare the transformed finding regions.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageOps

from .. import config
from .rules import _iou


def _gray(rgb: np.ndarray) -> tuple[np.ndarray, float]:
    scale = min(1.0, 640 / max(rgb.shape[:2]))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    if scale < 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return gray, scale


def register(image: np.ndarray, frame: np.ndarray) -> tuple[np.ndarray, float, float, int] | None:
    """Return image→frame homography in reduced coordinates, scales and inliers."""
    a, sa = _gray(image)
    b, sb = _gray(frame)
    orb = cv2.ORB_create(nfeatures=2000)
    ka, da = orb.detectAndCompute(a, None)
    kb, db = orb.detectAndCompute(b, None)
    if da is None or db is None or min(len(ka), len(kb)) < 12:
        return None
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da, db, k=2)
    good = [p[0] for p in pairs if len(p) == 2 and p[0].distance < 0.7 * p[1].distance]
    if len(good) < 12:
        return None
    src = np.float32([ka[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kb[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    cv2.setRNGSeed(config.SEED)
    h, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    n = int(mask.sum()) if mask is not None else 0
    if h is None or not np.isfinite(h).all() or n < 12 or n / len(good) < 0.6:
        return None
    # Require spatially spread matches rather than one coincidental textured patch.
    inliers = src[mask.ravel().astype(bool)]
    area = cv2.contourArea(cv2.convexHull(inliers))
    if area < 0.05 * a.shape[0] * a.shape[1]:
        return None
    corners = np.float32([[0, 0], [a.shape[1], 0], [a.shape[1], a.shape[0]], [0, a.shape[0]]]).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(corners, h)
    if not np.isfinite(projected).all() or not cv2.isContourConvex(projected):
        return None
    relative = cv2.contourArea(projected) / (b.shape[0] * b.shape[1])
    if not 0.1 <= relative <= 4:
        return None
    return h, sa, sb, n


def region_match(image: np.ndarray, frame: np.ndarray, iloc: dict, vloc: dict, registration=None) -> dict | None:
    registration = registration if registration is not None else register(image, frame)
    if registration is None:
        return None
    h, sa, sb, n = registration
    iw, ih = iloc.get("image_w"), iloc.get("image_h")
    vw, vh = vloc.get("image_w"), vloc.get("image_h")
    if not all(isinstance(x, (int, float)) and x > 0 for x in (iw, ih, vw, vh)):
        return None
    x, y, w, ht = (iloc[k] for k in ("x", "y", "w", "h"))
    points = np.float32([[x, y], [x + w, y], [x + w, y + ht], [x, y + ht]])
    points *= [image.shape[1] / iw * sa, image.shape[0] / ih * sa]
    moved = cv2.perspectiveTransform(points.reshape(-1, 1, 2), h).reshape(-1, 2)
    if not np.isfinite(moved).all():
        return None
    moved /= [frame.shape[1] * sb, frame.shape[0] * sb]
    low, high = moved.min(axis=0), moved.max(axis=0)
    mapped = (*low, *(high - low))
    target = (vloc["x"] / vw, vloc["y"] / vh, vloc["w"] / vw, vloc["h"] / vh)
    overlap = _iou(mapped, target)
    return {"verified": True, "method": "ORB + RANSAC image/frame registration",
            "inliers": n, "iou": round(float(overlap), 4)} if overlap >= 0.3 else None


def verify_regions(findings: list[dict], contexts: list) -> None:
    images = [f for f in findings if f["modality"] == "image" and f["location"].get("type") == "bbox"]
    videos = [f for f in findings if f["indicator"] in ("face_flicker", "frame_ela_inconsistency", "frame_noise_inconsistency")
              and f["location"].get("w")]
    if not images or not videos:
        return
    by_label = {c.label: c for c in contexts}
    # Each candidate pair is isolated: absent/undecodable frames never create support.
    cache = {}
    for i in images:
        for v in videos:
            ic, vc = by_label[i["evidence"]], by_label[v["evidence"]]
            key = (ic.label, vc.label, float(v["location"].get("start", 0)))
            try:
                if key not in cache:
                    if len(cache) >= 2:
                        cache.pop(next(iter(cache)))
                    with Image.open(ic.original) as im:
                        image = np.array(ImageOps.exif_transpose(im).convert("RGB"))
                    cap = cv2.VideoCapture(str(vc.original))
                    try:
                        cap.set(cv2.CAP_PROP_POS_MSEC, key[2] * 1000)
                        ok, frame = cap.read()
                    finally:
                        cap.release()
                    if not ok:
                        cache[key] = None
                    else:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        cache[key] = (image, frame, register(image, frame))
                pair = cache[key]
                if pair is None or pair[2] is None:
                    continue
                proof = region_match(pair[0], pair[1], i["location"], v["location"], pair[2])
                if proof:
                    ic.extra.setdefault("region_matches", {})[f"{i['finding_id']}:{v['finding_id']}"] = proof
            except (OSError, ValueError, cv2.error):
                continue

"""Shared image helpers: loading, block statistics, region extraction and heatmap rendering."""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage

from ... import config

HEATMAP_MAX_SIDE = 1600   # artifacts are downscaled to this for the UI and the report


def load_rgb(path: Path) -> np.ndarray:
    """Decode with EXIF orientation applied, so region coordinates match what a browser displays."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        return np.asarray(img.convert("RGB"), dtype=np.uint8)


def jpeg_roundtrip(rgb: np.ndarray, quality: int) -> np.ndarray:
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "JPEG", quality=quality, subsampling=0 if quality >= 90 else 2)
    buf.seek(0)
    with Image.open(buf) as im:
        return np.asarray(im.convert("RGB"), dtype=np.uint8)


def block_reduce(arr: np.ndarray, block: int, fn=np.mean) -> np.ndarray:
    """Per-block statistic over a 2-D array, cropping the ragged edge."""
    h, w = arr.shape[:2]
    hb, wb = h // block, w // block
    if hb == 0 or wb == 0:
        return np.zeros((0, 0))
    a = arr[: hb * block, : wb * block].reshape(hb, block, wb, block).transpose(0, 2, 1, 3)
    return fn(a.reshape(hb, wb, block * block), axis=2)


def robust_z(blocks: np.ndarray) -> np.ndarray:
    med = np.median(blocks)
    mad = np.median(np.abs(blocks - med)) * 1.4826
    if mad < 1e-9:
        mad = max(float(np.std(blocks)), 1e-9)
    return (blocks - med) / mad


@dataclass
class Region:
    x: int
    y: int
    w: int
    h: int
    mean_z: float
    peak_z: float
    area_fraction: float


def regions_from_mask(mask: np.ndarray, z: np.ndarray, block: int, img_w: int, img_h: int,
                      max_regions: int = 3, min_fraction: float | None = None) -> list[Region]:
    """Connected flagged blocks → bounding boxes in pixel coordinates, largest evidence first."""
    if mask.size == 0 or not mask.any():
        return []
    grown = ndimage.binary_closing(mask, structure=np.ones((3, 3)))
    labels, n = ndimage.label(grown)
    out: list[Region] = []
    total = mask.size
    for i in range(1, n + 1):
        sel = labels == i
        flagged = sel & mask
        if flagged.sum() == 0:
            continue
        frac = sel.sum() / total
        if frac < (config.MIN_REGION_FRACTION if min_fraction is None else min_fraction) or frac > 0.6:   # >60%: a global property, not a region
            continue
        ys, xs = np.where(sel)
        out.append(Region(x=int(xs.min() * block), y=int(ys.min() * block),
                          w=int((xs.max() - xs.min() + 1) * block), h=int((ys.max() - ys.min() + 1) * block),
                          mean_z=float(z[flagged].mean()), peak_z=float(z[flagged].max()), area_fraction=float(frac)))
    out.sort(key=lambda r: (-(r.mean_z * np.sqrt(r.area_fraction)), r.y, r.x))
    for r in out:
        r.w = min(r.w, img_w - r.x)
        r.h = min(r.h, img_h - r.y)
    return out[:max_regions]


def save_heatmap(values: np.ndarray, path: Path, out_w: int, out_h: int, lo: float, hi: float) -> None:
    """RGBA heatmap: transparent where unremarkable, TruthLens yellow where the signal is high."""
    v = np.clip((values.astype(np.float32) - lo) / max(hi - lo, 1e-6), 0, 1)
    scale = min(1.0, HEATMAP_MAX_SIDE / max(out_w, out_h))
    size = (max(1, int(out_w * scale)), max(1, int(out_h * scale)))
    alpha = Image.fromarray((v * 235).astype(np.uint8), "L").resize(size, Image.BILINEAR)
    rgba = Image.new("RGBA", size, (255, 210, 63, 0))
    rgba.putalpha(alpha)
    rgba.save(path, optimize=False)


def bbox_location(r: Region, img_w: int, img_h: int) -> dict:
    return {"type": "bbox", "x": r.x, "y": r.y, "w": r.w, "h": r.h, "image_w": img_w, "image_h": img_h}


def describe_position(r: Region, img_w: int, img_h: int) -> str:
    cx, cy = (r.x + r.w / 2) / img_w, (r.y + r.h / 2) / img_h
    vert = "upper" if cy < 0.34 else "lower" if cy > 0.66 else "middle"
    horiz = "left" if cx < 0.34 else "right" if cx > 0.66 else "centre"
    return "centre" if vert == "middle" and horiz == "centre" else f"{vert} {horiz}"

"""JPEG ghost / double compression (§3.3).

Re-save at q = 50..95 and record each block's difference curve. A region compressed at another
quality before being combined has a curve whose shape departs from the rest of the image.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from ... import config
from ..base import AnalysisContext, RawFinding, squash
from .common import (bbox_location, block_reduce, describe_position, jpeg_roundtrip, load_rgb, regions_from_mask,
                     robust_z, save_heatmap)

BLOCK = 16
GHOST_Z = 4.0
MIN_FRACTION = 0.012   # ghost needs a contiguous area; single noisy blocks are common
ALTERNATIVES = ["Uniform areas (sky, walls) have flat difference curves and can mislead",
                "Images recompressed several times by different apps"]


def ghost_deviation(rgb: np.ndarray, final_q: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Robust z of how far each block's re-save curve departs from the image-wide curve shape.

    Returns (z, informative mask, per-block quality where the block's curve dips lowest)."""
    base = rgb.astype(np.float32)
    curves = np.stack([block_reduce(((base - jpeg_roundtrip(rgb, q).astype(np.float32)) ** 2).mean(axis=2), BLOCK)
                       for q in config.GHOST_QUALITIES])
    energy = curves.mean(axis=0)
    informative = (energy > np.percentile(energy, 25)) & (energy > 1.0)
    shape = np.log(curves + 0.5) - np.log(energy + 0.5)[None]        # log shape: insensitive to texture level
    glob = np.median(shape[:, informative], axis=1)
    low = [i for i, q in enumerate(config.GHOST_QUALITIES) if q <= final_q - 5] or [0]
    dev = np.abs(shape[low] - glob[low, None, None]).mean(axis=0)
    dev = np.where(informative, dev, np.median(dev[informative]) if informative.any() else 0.0)
    z = robust_z(ndimage.uniform_filter(dev, 3))
    dip_q = np.array(config.GHOST_QUALITIES)[low][np.argmin(shape[low] - glob[low, None, None], axis=0)]
    return z, informative, dip_q


def analyze_array(rgb: np.ndarray, ctx: AnalysisContext, final_q: int) -> list[RawFinding]:
    h, w = rgb.shape[:2]
    z, informative, dip_q = ghost_deviation(rgb, final_q)
    if informative.sum() < 20:
        return []
    save_heatmap(np.kron(np.clip(z, 0, None), np.ones((BLOCK, BLOCK))), ctx.artifact("ghost.png"), w, h,
                 lo=2.0, hi=GHOST_Z * 1.6)
    mask = (z > GHOST_Z) & informative
    findings = []
    for r in regions_from_mask(mask, z, BLOCK, w, h, max_regions=2, min_fraction=MIN_FRACTION):
        ys = slice(r.y // BLOCK, (r.y + r.h) // BLOCK + 1)
        xs = slice(r.x // BLOCK, (r.x + r.w) // BLOCK + 1)
        region_q = int(np.median(dip_q[ys, xs][mask[ys, xs]]))
        where = describe_position(r, w, h)
        findings.append(RawFinding(
            indicator="jpeg_ghost", family="jpeg_ghost", name="JPEG ghost (separate compression)",
            location=bbox_location(r, w, h), loc_label=f"{where.capitalize()} region · {r.w}×{r.h} px",
            raw_score=squash(r.mean_z, mid=GHOST_Z + 2.0, scale=1.0),
            method=f"Re-saved at q={config.GHOST_QUALITIES[0]}–{config.GHOST_QUALITIES[-1]}; per-block difference-curve "
                   f"shape vs the image-wide shape. Region deviation {r.mean_z:.1f}·MAD (threshold {GHOST_Z:g}); file saved at q≈{final_q}",
            explanation=f"Blocks in the {where} region respond to re-compression differently from the rest of the image, "
                        f"so they carry a different compression history. Areas saved separately before being combined leave this trace.",
            alternatives=ALTERNATIVES, artifacts=["ghost.png"], sort=r.y + r.x / 1e5,
            extra={"mean_z": round(r.mean_z, 3), "dip_q": region_q, "final_q": final_q}))
    return findings


def run(ctx: AnalysisContext) -> list[RawFinding]:
    if ctx.metadata.get("format") != "JPEG":
        ctx.log("image", "JPEG ghost skipped: file is not JPEG")
        return []
    return analyze_array(load_rgb(ctx.original), ctx, int(ctx.metadata.get("jpeg_quality") or 95))

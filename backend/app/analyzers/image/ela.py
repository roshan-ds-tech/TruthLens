"""Error Level Analysis (§3.3): re-save at JPEG q=90 and look for blocks that recompress differently."""
from __future__ import annotations

import cv2
import numpy as np

from ... import config
from ..base import AnalysisContext, RawFinding, squash
from .common import (bbox_location, block_reduce, describe_position, jpeg_roundtrip, load_rgb, regions_from_mask,
                     robust_z, save_heatmap)

ALTERNATIVES = ["Recompression by a social platform or messaging app",
                "Sharp edges, text or logos, which always recompress with higher error"]


def ela_map(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-block ELA error normalised for local texture, and its robust z-score.

    Raw ELA is high on any sharp edge, so the block error is divided by the block's gradient energy;
    what remains is error that the texture does not explain.
    """
    from scipy import ndimage

    resaved = jpeg_roundtrip(rgb, config.ELA_QUALITY)
    err = np.abs(rgb.astype(np.int16) - resaved.astype(np.int16)).mean(axis=2).astype(np.float32)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    texture = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    b = config.ELA_BLOCK
    err_b = block_reduce(err, b)
    tex_b = block_reduce(texture, b)
    norm = err_b / (tex_b + 4.0)
    # Average over neighbouring blocks: a pasted region is contiguous, a noisy edge block is not.
    return norm, robust_z(ndimage.uniform_filter(norm, 3))


def analyze_array(rgb: np.ndarray, ctx: AnalysisContext, prefix: str = "", is_jpeg: bool = True,
                  sort_offset: float = 0.0, extra_loc: dict | None = None) -> list[RawFinding]:
    h, w = rgb.shape[:2]
    norm, z = ela_map(rgb)
    if z.size == 0:
        return []
    save_heatmap(np.kron(np.clip(z, 0, None), np.ones((config.ELA_BLOCK, config.ELA_BLOCK))),
                 ctx.artifact(f"{prefix}ela.png"), w, h, lo=2.0, hi=config.ELA_K_MAD * 1.6)
    mask = z > config.ELA_K_MAD
    findings = []
    for r in regions_from_mask(mask, z, config.ELA_BLOCK, w, h, min_fraction=0.008):
        raw = squash(r.mean_z, mid=config.ELA_K_MAD + 1.0, scale=0.6)
        if not is_jpeg:
            raw *= 0.7
        where = describe_position(r, w, h)
        loc = bbox_location(r, w, h) | (extra_loc or {})
        findings.append(RawFinding(
            indicator="ela_inconsistency", family="ela", name="Error level inconsistency",
            location=loc, loc_label=f"{where.capitalize()} region · {r.w}×{r.h} px",
            raw_score=raw,
            method=f"JPEG re-save at q={config.ELA_QUALITY}, texture-normalised block error, "
                   f"{config.ELA_BLOCK}px blocks; region mean {r.mean_z:.1f}·MAD above the image median (threshold {config.ELA_K_MAD:g})",
            explanation=f"The {where} region recompresses with {r.mean_z:.1f} times the median absolute deviation more "
                        f"error than the rest of the image, after allowing for local texture. A pasted or retouched area "
                        f"often carries a different compression history.",
            alternatives=ALTERNATIVES + ([] if is_jpeg else ["The file was never JPEG, so error levels are less meaningful"]),
            artifacts=[f"{prefix}ela.png"], sort=sort_offset + r.y + r.x / 1e5,
            extra={"mean_z": round(r.mean_z, 3), "area_fraction": round(r.area_fraction, 4)}))
    return findings


def run(ctx: AnalysisContext) -> list[RawFinding]:
    rgb = load_rgb(ctx.original)
    return analyze_array(rgb, ctx, is_jpeg=ctx.metadata.get("format") == "JPEG")

"""Noise-residual inconsistency (§3.3): residual = image − denoised; flag blocks with robust |z| > 3."""
from __future__ import annotations

import cv2
import numpy as np

from ... import config
from ..base import AnalysisContext, RawFinding, squash
from .common import bbox_location, block_reduce, describe_position, load_rgb, regions_from_mask, robust_z, save_heatmap

ALTERNATIVES = ["Mixed focus or background blur (bokeh) changes visible noise",
                "Local denoising or sharpening applied by the phone camera"]
MAX_SIDE = 2000


def residual_map(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    den = cv2.medianBlur(gray, 3)
    resid = gray.astype(np.float32) - den.astype(np.float32)
    b = config.NOISE_BLOCK
    var_b = block_reduce(resid, b, np.var)
    tex_b = block_reduce(den.astype(np.float32), b, np.std)
    logv = np.log(var_b + 0.05)
    return logv, robust_z(logv), tex_b


def analyze_array(rgb: np.ndarray, ctx: AnalysisContext, prefix: str = "", sort_offset: float = 0.0,
                  extra_loc: dict | None = None) -> list[RawFinding]:
    h0, w0 = rgb.shape[:2]
    scale = min(1.0, MAX_SIDE / max(h0, w0))
    small = cv2.resize(rgb, (int(w0 * scale), int(h0 * scale)), interpolation=cv2.INTER_AREA) if scale < 1 else rgb
    h, w = small.shape[:2]
    _, z, tex = residual_map(small)
    if z.size == 0:
        return []
    save_heatmap(np.kron(np.abs(z), np.ones((config.NOISE_BLOCK, config.NOISE_BLOCK))),
                 ctx.artifact(f"{prefix}noise.png"), w0, h0, lo=1.5, hi=config.NOISE_Z * 1.8)
    # Too noisy anywhere, or too smooth where the block has visible structure (flat sky is naturally smooth).
    mask = (z > config.NOISE_Z) | ((z < -config.NOISE_Z) & (tex > 6.0))
    absz = np.abs(z)
    findings = []
    for r in regions_from_mask(mask, absz, config.NOISE_BLOCK, w, h):
        # back to original pixel coordinates
        r.x, r.y, r.w, r.h = (int(round(v / scale)) for v in (r.x, r.y, r.w, r.h))
        r.w, r.h = min(r.w, w0 - r.x), min(r.h, h0 - r.y)
        ys, xs = slice(int(r.y * scale) // config.NOISE_BLOCK, int((r.y + r.h) * scale) // config.NOISE_BLOCK + 1), \
            slice(int(r.x * scale) // config.NOISE_BLOCK, int((r.x + r.w) * scale) // config.NOISE_BLOCK + 1)
        sign = float(np.median(z[ys, xs]))
        direction = "finer (smoother)" if sign < 0 else "stronger"
        where = describe_position(r, w0, h0)
        findings.append(RawFinding(
            indicator="noise_inconsistency", family="noise", name="Noise map discontinuity",
            location=bbox_location(r, w0, h0) | (extra_loc or {}), loc_label=f"{where.capitalize()} region · {r.w}×{r.h} px",
            raw_score=squash(r.mean_z, mid=config.NOISE_Z + 2.0, scale=1.2),
            method=f"3×3 median denoise, residual variance per {config.NOISE_BLOCK}px block, robust z; "
                   f"region mean |z| {r.mean_z:.1f} (threshold {config.NOISE_Z:g})",
            explanation=f"Sensor noise in the {where} region is {direction} than in the rest of the image "
                        f"(|z| = {r.mean_z:.1f}). Content from another camera or a retouched patch often has a different noise level.",
            alternatives=ALTERNATIVES, artifacts=[f"{prefix}noise.png"], sort=sort_offset + r.y + r.x / 1e5,
            extra={"mean_z": round(r.mean_z, 3), "direction": "smoother" if sign < 0 else "noisier"}))
    return findings


def run(ctx: AnalysisContext) -> list[RawFinding]:
    return analyze_array(load_rgb(ctx.original), ctx)

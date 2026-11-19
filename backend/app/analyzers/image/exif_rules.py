"""Metadata rules (§3.3): editor software tag, partial camera tags, capture vs modify date, thumbnail mismatch."""
from __future__ import annotations

import io
from datetime import datetime

import imagehash
from PIL import Image, ImageOps

from ... import config
from ...ingest.metadata import thumbnail_bytes
from ..base import AnalysisContext, RawFinding


def _file_loc(field: str) -> dict:
    return {"type": "file", "field": field}


def run(ctx: AnalysisContext) -> list[RawFinding]:
    meta = ctx.metadata
    exif: dict = meta.get("exif") or {}
    out: list[RawFinding] = []
    notes: list[str] = []

    if not exif:
        notes.append("No EXIF metadata. Messaging apps and social platforms usually strip it, so its absence is not an indicator.")

    software = exif.get("Software", "")
    hit = next((s for s in config.EDITOR_SOFTWARE if s in software.lower()), None)
    if hit:
        out.append(RawFinding(
            indicator="editor_software_tag", family="metadata", name="Editing software tag",
            location=_file_loc("Software"), loc_label=f"EXIF Software · {software}", raw_score=0.55,
            method="EXIF Software tag compared with a list of image editors",
            explanation=f"The file's Software tag reads \"{software}\", so it was last written by an image editor, not a camera.",
            alternatives=["Routine colour correction, cropping or resizing before publishing"], sort=0.1))

    if exif and not (exif.get("Make") or exif.get("Model")) and (exif.get("DateTimeOriginal") or software):
        out.append(RawFinding(
            indicator="camera_tags_missing", family="metadata", name="Camera make and model missing",
            location=_file_loc("Make"), loc_label="EXIF Make / Model absent", raw_score=0.35,
            method="EXIF present but Make and Model tags absent",
            explanation="The file keeps other EXIF fields but not the camera make and model, which editors and some export paths remove.",
            alternatives=["Screenshot or export from an app that writes partial EXIF"], sort=0.2))

    d_orig, d_mod = meta.get("date_original"), meta.get("date_modified")
    if d_orig and d_mod:
        gap = (datetime.fromisoformat(d_mod) - datetime.fromisoformat(d_orig)).total_seconds()
        if gap > 86400:
            days = gap / 86400
            out.append(RawFinding(
                indicator="modified_after_capture", family="metadata", name="Modified long after capture",
                location=_file_loc("DateTime"), loc_label=f"Captured {d_orig[:10]} · modified {d_mod[:10]}",
                raw_score=0.45 if days < 365 else 0.5,
                method="EXIF DateTimeOriginal compared with DateTime (last modification)",
                explanation=f"The photo was captured on {d_orig[:10]} but the file was last modified {days:.0f} days later.",
                alternatives=["Camera or phone clock set incorrectly", "Re-saved later without edits"], sort=0.3,
                extra={"captured": d_orig, "modified": d_mod}))

    thumb = thumbnail_bytes(ctx.original) if meta.get("format") == "JPEG" else None
    if thumb:
        try:
            with Image.open(io.BytesIO(thumb)) as t, Image.open(ctx.original) as main:
                t_rgb, m_rgb = t.convert("RGB"), ImageOps.exif_transpose(main).convert("RGB")
                ratio_t, ratio_m = t_rgb.width / t_rgb.height, m_rgb.width / m_rgb.height
                same_shape = abs(ratio_t - ratio_m) < 0.15 or abs(ratio_t - 1 / ratio_m) < 0.15
                dist = imagehash.phash(t_rgb) - imagehash.phash(m_rgb.resize(t_rgb.size))
            if same_shape and dist > 12:
                out.append(RawFinding(
                    indicator="thumbnail_mismatch", family="metadata", name="Thumbnail differs from main image",
                    location=_file_loc("JPEGThumbnail"), loc_label=f"EXIF thumbnail · pHash distance {dist}",
                    raw_score=0.8,
                    method=f"Perceptual hash of the embedded EXIF thumbnail vs the downscaled main image: distance {dist} (threshold 12)",
                    explanation="The preview thumbnail stored inside the file shows different content from the main image. "
                                "Editors that change pixels but keep the old metadata leave this mismatch.",
                    alternatives=["Thumbnail generated before a crop or rotation"], sort=0.4,
                    extra={"phash_distance": int(dist)}))
        except Exception as exc:  # unreadable thumbnail is a note, not a failure
            notes.append(f"EXIF thumbnail could not be compared ({exc.__class__.__name__}).")

    ctx.extra["metadata_notes"] = notes
    return out

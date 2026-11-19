"""Metadata extraction: EXIF (exifread + Pillow), container info (ffprobe), audio header (soundfile)."""
from __future__ import annotations

import io
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import exifread
from PIL import Image

# Standard JPEG luminance quantization table (quality 50), used to estimate the saved quality.
_STD_LUMA = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56,
             14, 17, 22, 29, 51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
             49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99]


class MetadataError(ValueError):
    pass


def tool_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        line = subprocess.run(["ffprobe", "-version"], capture_output=True, text=True, timeout=10).stdout.split("\n")[0]
        out["ffmpeg"] = line.split()[2] if len(line.split()) > 2 else line
    except Exception:  # pragma: no cover - ffmpeg missing
        out["ffmpeg"] = "missing"
    return out


def estimate_jpeg_quality(img: Image.Image) -> Optional[int]:
    q = getattr(img, "quantization", None)
    if not q or 0 not in q:
        return None
    table = list(q[0])
    if len(table) != 64:
        return None
    # Invert the libjpeg scaling: table = (std * S + 50) / 100, S = 5000/Q (Q<50) or 200-2Q.
    scales = [(t * 100 - 50) / s for t, s in zip(table, _STD_LUMA) if s]
    scale = sorted(scales)[len(scales) // 2]
    quality = (200 - scale) / 2 if scale <= 100 else 5000 / max(scale, 1e-6)
    return int(max(1, min(100, round(quality))))


def _parse_exif_date(value: str) -> Optional[str]:
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d"):
        try:
            return datetime.strptime(value.strip()[:19], fmt).isoformat()
        except ValueError:
            continue
    return None


def _gps_to_deg(values: Any, ref: str) -> Optional[float]:
    try:
        d, m, s = [float(v.num) / float(v.den) if v.den else 0.0 for v in values.values]
        deg = d + m / 60 + s / 3600
        return -deg if ref in ("S", "W") else deg
    except Exception:
        return None


def image_metadata(path: Path) -> dict[str, Any]:
    try:
        with Image.open(path) as img:
            img.load()
            meta: dict[str, Any] = {"width": img.width, "height": img.height, "format": img.format, "mode": img.mode,
                                    "jpeg_quality": estimate_jpeg_quality(img) if img.format == "JPEG" else None,
                                    "jpeg_tables": len(getattr(img, "quantization", {}) or {})}
    except Exception as exc:
        raise MetadataError(f"image could not be decoded: {exc}") from exc

    with open(path, "rb") as f:
        tags = exifread.process_file(f, details=True)
    exif: dict[str, str] = {}
    for key in ("Image Make", "Image Model", "Image Software", "Image DateTime", "EXIF DateTimeOriginal",
                "EXIF DateTimeDigitized", "EXIF ExifImageWidth", "EXIF ExifImageLength", "EXIF ColorSpace",
                "Image Orientation", "EXIF LensModel", "GPS GPSLatitudeRef", "GPS GPSLongitudeRef"):
        if key in tags:
            exif[key.split(" ", 1)[1]] = str(tags[key]).strip()
    if "GPS GPSLatitude" in tags and "GPS GPSLongitude" in tags:
        lat = _gps_to_deg(tags["GPS GPSLatitude"], exif.get("GPSLatitudeRef", "N"))
        lon = _gps_to_deg(tags["GPS GPSLongitude"], exif.get("GPSLongitudeRef", "E"))
        if lat is not None and lon is not None:
            meta["gps"] = {"lat": round(lat, 6), "lon": round(lon, 6)}
    meta["exif"] = exif
    meta["date_original"] = _parse_exif_date(exif["DateTimeOriginal"]) if "DateTimeOriginal" in exif else None
    meta["date_modified"] = _parse_exif_date(exif["DateTime"]) if "DateTime" in exif else None
    thumb = tags.get("JPEGThumbnail")
    if isinstance(thumb, (bytes, bytearray)) and thumb:
        try:
            with Image.open(io.BytesIO(thumb)) as t:
                meta["thumbnail"] = {"width": t.width, "height": t.height}
        except Exception:
            meta["thumbnail"] = {"error": "unreadable"}
    return meta


def thumbnail_bytes(path: Path) -> Optional[bytes]:
    with open(path, "rb") as f:
        tags = exifread.process_file(f, details=True)
    thumb = tags.get("JPEGThumbnail")
    return bytes(thumb) if isinstance(thumb, (bytes, bytearray)) and thumb else None


def ffprobe(path: Path) -> dict[str, Any]:
    proc = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise MetadataError(f"ffprobe could not read the file: {proc.stderr.strip()[:200]}")
    return json.loads(proc.stdout or "{}")


def _rate(value: Optional[str]) -> Optional[float]:
    if not value or value in ("0/0",):
        return None
    if "/" in value:
        n, d = value.split("/")
        return float(n) / float(d) if float(d) else None
    return float(value)


def av_metadata(path: Path) -> dict[str, Any]:
    info = ffprobe(path)
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    tags = {k.lower(): str(val) for k, val in (fmt.get("tags") or {}).items()}
    meta: dict[str, Any] = {
        "duration": float(fmt.get("duration") or (v or a or {}).get("duration") or 0.0),
        "container": fmt.get("format_name"),
        "bit_rate": int(fmt["bit_rate"]) if fmt.get("bit_rate") else None,
        "encoder": tags.get("encoder"),
        "creation_time": tags.get("creation_time"),
        "make": tags.get("com.apple.quicktime.make") or tags.get("make"),
        "model": tags.get("com.apple.quicktime.model") or tags.get("model"),
        "has_video": v is not None,
        "has_audio": a is not None,
    }
    if v is not None:
        meta.update({"video_codec": v.get("codec_name"), "width": v.get("width"), "height": v.get("height"),
                     "fps": _rate(v.get("avg_frame_rate")) or _rate(v.get("r_frame_rate")),
                     "r_frame_rate": v.get("r_frame_rate"), "avg_frame_rate": v.get("avg_frame_rate"),
                     "nb_frames": int(v["nb_frames"]) if str(v.get("nb_frames", "")).isdigit() else None,
                     "video_encoder": (v.get("tags") or {}).get("encoder")})
    if a is not None:
        meta.update({"audio_codec": a.get("codec_name"), "sample_rate": int(a.get("sample_rate") or 0),
                     "channels": a.get("channels")})
    if v is None and a is None:
        raise MetadataError("no audio or video stream found")
    return meta

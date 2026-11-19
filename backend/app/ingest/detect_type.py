"""Evidence type detection by magic bytes, never by extension (§3.2)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import filetype


class UnsupportedType(ValueError):
    pass


IMAGE_MIMES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/tiff": "tif", "image/bmp": "bmp"}
VIDEO_MIMES = {"video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm", "video/x-matroska": "mkv",
               "video/x-msvideo": "avi", "video/x-m4v": "m4v"}
AUDIO_MIMES = {"audio/x-aiff": "aiff", "audio/aiff": "aiff", "audio/x-wav": "wav", "audio/wav": "wav", "audio/mpeg": "mp3",
               "audio/ogg": "ogg", "audio/x-flac": "flac", "audio/flac": "flac", "audio/mp4": "m4a", "audio/aac": "aac", "audio/opus": "opus", "audio/webm": "webm"}


@dataclass(frozen=True)
class DetectedType:
    kind: str   # image | video | audio | text
    mime: str
    ext: str


def detect(path: Path) -> DetectedType:
    with open(path, "rb") as f:
        head = f.read(8192)
    kind = filetype.guess(head)
    if kind is not None:
        mime = kind.mime
        if mime in IMAGE_MIMES:
            return DetectedType("image", mime, IMAGE_MIMES[mime])
        if mime in VIDEO_MIMES:
            return DetectedType("video", mime, VIDEO_MIMES[mime])
        if mime in AUDIO_MIMES:
            return DetectedType("audio", mime, AUDIO_MIMES[mime])
        raise UnsupportedType(f"{mime} is not a supported evidence type")
    # No binary signature: accept UTF-8 text (captions, posts, claims).
    try:
        data = path.read_bytes()
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsupportedType("unrecognised binary file (no known magic bytes)") from exc
    if b"\x00" in data:
        raise UnsupportedType("unrecognised binary file (no known magic bytes)")
    return DetectedType("text", "text/plain", "txt")

"""Ingest: detect type, hash, seal the original read-only, extract metadata, log custody (§3.2)."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

from .. import config, custody
from ..models import Case, Evidence, JsonMixin, utcnow
from . import metadata as md
from .detect_type import DetectedType, UnsupportedType, detect

log = logging.getLogger("truthlens.ingest")


class IngestError(ValueError):
    """Rejected input. ``status`` is the HTTP code the API returns."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _fmt_size(n: int) -> str:
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB" if n >= 1024 else f"{n} B"
    return f"{n / (1024 * 1024):.1f} MB"


def _fmt_dur(s: float) -> str:
    s = max(0, int(round(s)))
    return f"{s // 60:02d}:{s % 60:02d}"


def meta_label(kind: str, size: int, meta: dict) -> str:
    """The one-line description the UI cards show, e.g. 'Video · 18.4 MB · 00:42 · 1280×720'."""
    if kind == "image":
        return f"Image · {meta.get('width')}×{meta.get('height')} · {_fmt_size(size)}"
    if kind == "video":
        parts = ["Video", _fmt_size(size), _fmt_dur(meta.get("duration", 0))]
        if meta.get("width"):
            parts.append(f"{meta['width']}×{meta['height']}")
        return " · ".join(parts)
    if kind == "audio":
        sr = meta.get("sample_rate")
        parts = ["Audio", _fmt_dur(meta.get("duration", 0))]
        if sr:
            parts.append(f"{sr / 1000:g} kHz")
        return " · ".join(parts)
    return f"Text · {meta.get('chars', 0)} characters"


def _next_label(s: Session, case_id: str) -> tuple[str, int]:
    rows = list(s.exec(select(Evidence).where(Evidence.case_id == case_id)))
    n = len(rows) + 1
    return f"E-{n:02d}", n


def _check_limits(kind: str, size: int, meta: dict) -> list[str]:
    """Reject what cannot be analyzed; return warnings for what will be trimmed or downscaled."""
    warnings: list[str] = []
    if kind == "image" and size > config.MAX_IMAGE_BYTES:
        raise IngestError(f"Image is {_fmt_size(size)}; the limit is 20 MB.", 413)
    if kind == "video":
        if not meta.get("has_video"):
            raise IngestError("File has no video stream.")
        if meta.get("duration", 0) > config.MAX_VIDEO_SECONDS:
            warnings.append(f"Video is {meta['duration']:.0f} s; only the first {config.MAX_VIDEO_SECONDS:.0f} s are analyzed.")
        if (meta.get("height") or 0) > config.MAX_VIDEO_HEIGHT:
            warnings.append(f"Video is {meta['height']}p; frames are downscaled to {config.MAX_VIDEO_HEIGHT}p for analysis.")
    if kind == "audio" and meta.get("duration", 0) > config.MAX_AUDIO_SECONDS:
        warnings.append(f"Audio is {meta['duration']:.0f} s; only the first {config.MAX_AUDIO_SECONDS:.0f} s are analyzed.")
    if kind == "text" and meta.get("chars", 0) > config.MAX_TEXT_CHARS:
        raise IngestError(f"Text is longer than {config.MAX_TEXT_CHARS} characters.", 413)
    return warnings


def _extract_metadata(kind: str, path: Path) -> dict:
    try:
        if kind == "image":
            return md.image_metadata(path)
        if kind in ("video", "audio"):
            return md.av_metadata(path)
        text = path.read_text("utf-8")
        return {"chars": len(text)}
    except md.MetadataError as exc:
        # The decoder's message names the temporary upload path; keep it in the server log only.
        log.warning("unreadable %s upload: %s", kind, exc)
        noun = {"image": "image", "video": "video", "audio": "audio file"}.get(kind, "file")
        raise IngestError(f"Could not read this {noun}: it looks corrupt, truncated or in an unsupported encoding.", 422) from exc


def ingest_file(s: Session, case: Case, src: Path, filename: str, actor: str,
                source_note: Optional[str] = None) -> Evidence:
    size = src.stat().st_size
    if size == 0:
        raise IngestError("File is empty.")
    if size > config.MAX_UPLOAD_BYTES:
        raise IngestError("File is larger than 200 MB.", 413)
    try:
        dt: DetectedType = detect(src)
    except UnsupportedType as exc:
        raise IngestError(f"Unsupported file type: {exc}.", 415) from exc

    sha = custody.sha256_file(src)
    existing = s.exec(select(Evidence).where(Evidence.case_id == case.id, Evidence.sha256 == sha)).first()
    if existing:
        return existing

    meta = _extract_metadata(dt.kind, src)
    if dt.kind == "video" and meta.get("has_video") is False and meta.get("has_audio"):
        dt = DetectedType("audio", "audio/mp4", "m4a")   # an .mp4/.m4a container that only holds audio
    meta["warnings"] = _check_limits(dt.kind, size, meta)
    if source_note:
        meta["source"] = source_note

    custody.store_original(case.id, src, sha, dt.ext)
    label, order = _next_label(s, case.id)
    ev = Evidence(case_id=case.id, label=label, kind=dt.kind, filename=filename, sha256=sha, size=size,
                  mime=dt.mime, metadata_json=JsonMixin.dumps(meta), order_idx=order)
    s.add(ev)
    case.updated_at = utcnow()
    s.add(case)
    s.commit()
    s.refresh(ev)
    noun = {"image": "Image", "video": "Video", "audio": "Audio", "text": "Text"}[dt.kind]
    custody.log(s, case.id, actor, f"{noun} ingested and sealed · {label}", f"tl-ingest {config.APP_VERSION}",
                "upload stream", f"sha256 {sha}")
    if dt.kind == "video" and meta.get("has_audio"):
        _extract_audio_track(s, case, ev, actor)
    return ev


def ingest_text(s: Session, case: Case, text: str, actor: str, source_note: str = "Pasted caption or claim") -> Evidence:
    text = text.strip()
    if not text:
        raise IngestError("Text is empty.")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "caption.txt"
        p.write_text(text, "utf-8")
        return ingest_file(s, case, p, "Caption · " + source_note, actor, source_note)


def _extract_audio_track(s: Session, case: Case, video: Evidence, actor: str) -> Evidence:
    """Derive the clip's audio as its own evidence item (16 kHz mono WAV, bit-exact so reruns match)."""
    src = custody.original_path(case.id, video.sha256)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "track.wav"
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-t", str(config.MAX_VIDEO_SECONDS), "-vn", "-ac", "1",
               "-ar", str(config.AUDIO_SR), "-c:a", "pcm_s16le", "-fflags", "+bitexact", "-flags:a", "+bitexact",
               "-map_metadata", "-1", str(wav)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0 or not wav.exists():
            custody.log(s, case.id, "system", f"Audio track extraction failed · {video.label}",
                        f"ffmpeg {md.tool_versions()['ffmpeg']}", f"sha256 {video.sha256}", "—")
            return video
        sha = custody.sha256_file(wav)
        meta = md.av_metadata(wav)
        meta["derived_from"] = video.label
        meta["warnings"] = []
        custody.store_original(case.id, wav, sha, "wav")
        label, order = _next_label(s, case.id)
        ev = Evidence(case_id=case.id, label=label, kind="audio", filename=f"Audio track (from {video.filename})",
                      sha256=sha, size=wav.stat().st_size, mime="audio/x-wav", metadata_json=JsonMixin.dumps(meta),
                      parent_id=video.id, order_idx=order)
        s.add(ev)
        s.commit()
        s.refresh(ev)
    custody.log(s, case.id, "system", f"Audio track extracted · {label}", f"ffmpeg {md.tool_versions()['ffmpeg']} (pinned flags)",
                f"sha256 {video.sha256}", f"sha256 {sha}")
    return ev


def copy_upload_to_temp(fileobj, suffix: str = "") -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    with tmp:
        shutil.copyfileobj(fileobj, tmp)
    return Path(tmp.name)

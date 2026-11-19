"""Audio decoding (ffmpeg → derived WAV), waveform peaks and the spectrogram artifact."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
from PIL import Image

from ... import config
from ..base import AnalysisContext


def decode(src: Path, dest: Path, sr: Optional[int], max_s: float) -> Path:
    """Decode any audio/video file to a mono 16-bit WAV. ``sr=None`` keeps the native rate."""
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-t", str(max_s), "-vn", "-ac", "1"]
    if sr:
        cmd += ["-ar", str(sr)]
    cmd += ["-c:a", "pcm_s16le", "-fflags", "+bitexact", "-flags:a", "+bitexact", "-map_metadata", "-1", str(dest)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg could not decode audio: {proc.stderr.strip()[:200]}")
    return dest


def load_16k(ctx: AnalysisContext) -> tuple[np.ndarray, int]:
    if "_y16" not in ctx.extra:
        wav = decode(ctx.original, ctx.derived_dir / "audio_16k.wav", config.AUDIO_SR, config.MAX_AUDIO_SECONDS)
        y, sr = sf.read(wav, dtype="float32")
        ctx.extra["_y16"] = (y, sr)
    return ctx.extra["_y16"]


def native_source(ctx: AnalysisContext) -> Path:
    """For an audio track derived from a video, go back to the video for the native sample rate."""
    parent = ctx.metadata.get("derived_from")
    if parent:
        for other in ctx.case_evidence:
            if other.label == parent:
                return other.original
    return ctx.original


def load_native(ctx: AnalysisContext) -> tuple[np.ndarray, int]:
    wav = decode(native_source(ctx), ctx.derived_dir / "audio_native.wav", None, config.MAX_AUDIO_SECONDS)
    y, sr = sf.read(wav, dtype="float32")
    return y, sr


def frame_rms_db(y: np.ndarray, sr: int, frame_s: float, hop_s: float) -> tuple[np.ndarray, np.ndarray]:
    n, h = int(sr * frame_s), int(sr * hop_s)
    if len(y) < n:
        return np.zeros(0), np.zeros(0)
    idx = np.arange(0, len(y) - n + 1, h)
    frames = np.lib.stride_tricks.sliding_window_view(y, n)[idx]
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-9), (idx + n / 2) / sr


def waveform_peaks(y: np.ndarray, buckets: int = 140) -> list[float]:
    if len(y) == 0:
        return [0.0] * buckets
    chunks = np.array_split(np.abs(y), buckets)
    peaks = np.array([float(c.max()) if len(c) else 0.0 for c in chunks])
    top = peaks.max() or 1.0
    return [round(float(p / top), 4) for p in peaks]


def render_spectrogram(y: np.ndarray, sr: int, path: Path, width: int = 1000, height: int = 150) -> None:
    """Greyscale spectrogram (0–8 kHz) in the UI's palette: light background, dark energy."""
    n_fft, hop = 512, max(1, len(y) // width) if len(y) > width else 64
    if len(y) < n_fft:
        y = np.pad(y, (0, n_fft - len(y)))
    win = np.hanning(n_fft).astype(np.float32)
    starts = np.arange(0, len(y) - n_fft + 1, hop)
    frames = np.lib.stride_tricks.sliding_window_view(y, n_fft)[starts] * win
    spec = np.abs(np.fft.rfft(frames, axis=1)).T          # (freq, time)
    db = 20 * np.log10(spec + 1e-6)
    db = np.clip((db - (db.max() - 80)) / 80, 0, 1)       # 80 dB dynamic range
    g = (247 - db * 210).astype(np.uint8)[::-1]            # low frequencies at the bottom
    img = Image.fromarray(g, "L").resize((width, height), Image.BILINEAR).convert("RGB")
    img.save(path)

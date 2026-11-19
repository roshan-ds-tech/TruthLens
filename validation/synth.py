"""Seeded generators for evidence with known ground truth (used by tests and the validation harness).

Sources are the public-domain sample photos bundled with scikit-image (no network). Every generator
takes a seed and is deterministic, so the test set is reproducible.
"""
from __future__ import annotations

import io
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

# ------------------------------------------------------------------ images

PHOTO_FILES = ["astronaut.png", "chelsea.png", "coffee.png", "rocket.jpg", "motorcycle_left.png", "motorcycle_right.png",
               "ihc.png", "color.png"]


def photos() -> list[tuple[str, np.ndarray]]:
    import skimage

    d = Path(skimage.__file__).parent / "data"
    out = []
    for name in PHOTO_FILES:
        p = d / name
        if p.exists():
            with Image.open(p) as im:
                out.append((p.stem, np.asarray(im.convert("RGB"))))
    return out


def crops(rgb: np.ndarray, size: int, n: int, rng: np.random.Generator) -> list[np.ndarray]:
    h, w = rgb.shape[:2]
    if h < size or w < size:
        scale = size / min(h, w)
        rgb = cv2.resize(rgb, (int(w * scale) + 1, int(h * scale) + 1), interpolation=cv2.INTER_CUBIC)
        h, w = rgb.shape[:2]
    out = []
    for _ in range(n):
        y, x = int(rng.integers(0, h - size + 1)), int(rng.integers(0, w - size + 1))
        c = rgb[y:y + size, x:x + size]
        out.append(c[:, ::-1].copy() if rng.random() < 0.5 else c.copy())
    return out


def jpeg(rgb: np.ndarray, q: int, exif: Optional[dict] = None, thumb: Optional[np.ndarray] = None) -> bytes:
    """Encode as JPEG with optional camera-style EXIF (Make, Model, DateTimeOriginal, Software…)."""
    img = Image.fromarray(rgb)
    ex = Image.Exif()
    if exif:
        tags = {"Make": 0x010F, "Model": 0x0110, "Software": 0x0131, "DateTime": 0x0132}
        for k, tag in tags.items():
            if k in exif:
                ex[tag] = exif[k]
        if "DateTimeOriginal" in exif:
            ex.get_ifd(0x8769)[0x9003] = exif["DateTimeOriginal"]
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=q, exif=ex.tobytes() if exif else b"")
    data = buf.getvalue()
    if thumb is not None:
        data = _with_thumbnail(data, thumb)
    return data


def _with_thumbnail(jpeg_bytes: bytes, thumb_rgb: np.ndarray) -> bytes:
    """Embed an EXIF thumbnail (IFD1) using piexif-free manual construction via Pillow's exif support."""
    img = Image.open(io.BytesIO(jpeg_bytes))
    ex = img.getexif()
    tb = io.BytesIO()
    tw = 160
    Image.fromarray(thumb_rgb).resize((tw, max(1, round(tw * img.height / img.width)))).save(tb, "JPEG", quality=80)
    # Pillow writes IFD1 thumbnails only through the raw EXIF block; fall back to a JPEG APP1 with IFD1.
    raw = _exif_with_ifd1(ex.tobytes(), tb.getvalue())
    out = io.BytesIO()
    img.save(out, "JPEG", quality="keep", exif=raw)
    return out.getvalue()


def _exif_with_ifd1(exif_bytes: bytes, thumb: bytes) -> bytes:
    """Append an IFD1 (JPEGInterchangeFormat) pointing at ``thumb`` to a TIFF EXIF block (either byte order)."""
    import struct

    assert exif_bytes[:6] == b"Exif\x00\x00"
    tiff = bytearray(exif_bytes[6:])
    e = "<" if tiff[:2] == b"II" else ">"
    ifd0 = struct.unpack_from(e + "I", tiff, 4)[0]
    n = struct.unpack_from(e + "H", tiff, ifd0)[0]
    next_ptr_pos = ifd0 + 2 + 12 * n
    ifd1_off = len(tiff)
    entries = [(0x0201, 4, 1, ifd1_off + 2 + 12 * 2 + 4), (0x0202, 4, 1, len(thumb))]
    ifd1 = struct.pack(e + "H", len(entries))
    for tag, typ, cnt, val in entries:
        ifd1 += struct.pack(e + "HHII", tag, typ, cnt, val)
    ifd1 += struct.pack(e + "I", 0)
    struct.pack_into(e + "I", tiff, next_ptr_pos, ifd1_off)
    return b"Exif\x00\x00" + bytes(tiff) + ifd1 + thumb


def jpeg_rgb(rgb: np.ndarray, q: int) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(jpeg(rgb, q))).convert("RGB"))


@dataclass
class Tampered:
    data: bytes
    mask: np.ndarray       # bool, True where pixels were changed
    kind: str
    params: dict


def splice(base: np.ndarray, donor: np.ndarray, rng: np.random.Generator, base_q: int, final_q: int,
           frac: float = 0.09) -> Tampered:
    """Camera JPEG (base_q) + a pasted, resized patch from another photo, re-saved at final_q."""
    h, w = base.shape[:2]
    side = int(np.sqrt(frac * h * w))
    y, x = int(rng.integers(0, h - side)), int(rng.integers(0, w - side))
    patch = cv2.resize(donor, (side, side), interpolation=cv2.INTER_AREA)
    img = jpeg_rgb(base, base_q).copy()
    img[y:y + side, x:x + side] = patch
    mask = np.zeros((h, w), bool)
    mask[y:y + side, x:x + side] = True
    return Tampered(jpeg(img, final_q), mask, "splice", {"box": [x, y, side, side], "base_q": base_q, "final_q": final_q})


def copy_move(base: np.ndarray, rng: np.random.Generator, base_q: int, final_q: int, frac: float = 0.06) -> Tampered:
    """Clone a textured region to another place in the same image (flat sky would leave nothing to match)."""
    h, w = base.shape[:2]
    side = int(np.sqrt(frac * h * w))
    img = jpeg_rgb(base, base_q).copy()
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    texture = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
    best = None
    for _ in range(60):
        sy, sx = int(rng.integers(0, h - side)), int(rng.integers(0, w - side))
        score = float(texture[sy:sy + side, sx:sx + side].mean())
        if best is None or score > best[0]:
            best = (score, sy, sx)
    _, sy, sx = best
    for _ in range(200):
        dy, dx = int(rng.integers(0, h - side)), int(rng.integers(0, w - side))
        if abs(sy - dy) > side or abs(sx - dx) > side:
            break
    img[dy:dy + side, dx:dx + side] = img[sy:sy + side, sx:sx + side]
    mask = np.zeros((h, w), bool)
    mask[dy:dy + side, dx:dx + side] = True
    return Tampered(jpeg(img, final_q), mask, "copy_move", {"src": [sx, sy], "dst": [dx, dy, side, side], "final_q": final_q})


def retouch(base: np.ndarray, rng: np.random.Generator, base_q: int, final_q: int, frac: float = 0.08) -> Tampered:
    """Local edit: smooth a region and shift its brightness (a typical clean-up or object removal)."""
    h, w = base.shape[:2]
    side = int(np.sqrt(frac * h * w))
    y, x = int(rng.integers(0, h - side)), int(rng.integers(0, w - side))
    img = jpeg_rgb(base, base_q).copy()
    region = cv2.GaussianBlur(img[y:y + side, x:x + side], (0, 0), 2.2).astype(np.int16) + int(rng.integers(8, 20))
    img[y:y + side, x:x + side] = np.clip(region, 0, 255).astype(np.uint8)
    mask = np.zeros((h, w), bool)
    mask[y:y + side, x:x + side] = True
    return Tampered(jpeg(img, final_q), mask, "retouch", {"box": [x, y, side, side], "final_q": final_q})


CAMERA_EXIF = {"Make": "samsung", "Model": "SM-A525F", "DateTimeOriginal": "2026:11:12 18:20:04", "DateTime": "2026:11:12 18:20:04"}

# ------------------------------------------------------------------ audio

def speech_like(seconds: float, seed: int, sr: int = 16000, f0: float = 140.0) -> np.ndarray:
    """Syllable-like voiced bursts (harmonics through moving formants) with pauses. Not intelligible."""
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    y = np.zeros(n, np.float32)
    t = 0.3
    while t < seconds - 0.4:
        dur = float(rng.uniform(0.12, 0.35))
        a, b = int(t * sr), int(min(seconds, t + dur) * sr)
        tt = np.arange(b - a) / sr
        pitch = f0 * (1 + 0.08 * np.sin(2 * np.pi * rng.uniform(1, 3) * tt) + rng.normal(0, 0.01))
        phase = 2 * np.pi * np.cumsum(pitch) / sr
        voiced = sum(np.sin(k * phase) / k for k in range(1, 12))
        env = np.sin(np.pi * np.linspace(0, 1, b - a)) ** 0.7
        y[a:b] += (0.25 * voiced * env).astype(np.float32)
        t += dur + (float(rng.uniform(0.25, 0.7)) if rng.random() < 0.25 else float(rng.uniform(0.03, 0.09)))
    # formant-ish colouring
    from scipy.signal import lfilter

    y = lfilter([1.0], [1.0, -0.6], y).astype(np.float32)
    return y / (np.abs(y).max() + 1e-6) * 0.5


def room_noise(n: int, seed: int, level_db: float, colour: float = 0.7) -> np.ndarray:
    from scipy.signal import lfilter

    rng = np.random.default_rng(seed)
    x = lfilter([1.0], [1.0, -colour], rng.normal(0, 1, n)).astype(np.float32)
    x /= np.sqrt(np.mean(x ** 2)) + 1e-9
    return x * (10 ** (level_db / 20))


def recording(seconds: float, seed: int, sr: int = 16000, noise_db: float = -52.0, colour: float = 0.7) -> np.ndarray:
    y = speech_like(seconds, seed, sr) + room_noise(int(seconds * sr), seed + 1000, noise_db, colour)
    return np.clip(y, -1, 1).astype(np.float32)


def spliced_recording(seconds: float, cut: float, seed: int, sr: int = 16000, step_db: float = 9.0) -> np.ndarray:
    """Two recordings with different room noise joined at ``cut`` seconds."""
    a = recording(cut, seed, sr, -54.0, 0.6)
    b = recording(seconds - cut, seed + 7, sr, -54.0 + step_db, 0.9)
    return np.concatenate([a, b]).astype(np.float32)


def band_limited(y: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Generate at a low rate and upsample, as many TTS systems do."""
    import librosa

    return librosa.resample(y, orig_sr=sr_in, target_sr=sr_out).astype(np.float32)


def write_wav(path: Path, y: np.ndarray, sr: int) -> None:
    import soundfile as sf

    sf.write(path, y, sr, subtype="PCM_16")


# ------------------------------------------------------------------ video

def pan_frames(rgb: np.ndarray, seconds: float, fps: int, size: tuple[int, int] = (320, 240), seed: int = 0) -> list[np.ndarray]:
    """A slow, slightly wobbling camera pan across a photo (continuous sub-pixel motion, one shot)."""
    rng = np.random.default_rng(seed)
    W, H = size
    big = cv2.resize(rgb, (int(W * 1.8), int(H * 1.8)), interpolation=cv2.INTER_CUBIC)
    n = int(seconds * fps)
    span_x, span_y = big.shape[1] - W - 8, big.shape[0] - H - 8
    wob = rng.uniform(0, 2 * np.pi)
    frames = []
    for i in range(n):
        u = i / max(n - 1, 1)
        x = 4 + span_x * (0.1 + 0.8 * u) + 2.5 * np.sin(wob + i / 7)
        y = 4 + span_y * (0.5 + 0.25 * np.sin(2 * np.pi * u * 0.5)) + 1.5 * np.cos(wob + i / 5)
        m = np.float32([[1, 0, -x], [0, 1, -y]])
        frames.append(cv2.warpAffine(big, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT))
    return frames


def write_video(path: Path, frames: list[np.ndarray], fps: int, audio: Optional[np.ndarray] = None, sr: int = 16000) -> None:
    """H.264 (libx264, single thread → bit-exact) with optional mono AAC audio."""
    path.parent.mkdir(parents=True, exist_ok=True)
    h, w = frames[0].shape[:2]
    tmp_wav = path.with_suffix(".tmp.wav")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
    if audio is not None:
        write_wav(tmp_wav, audio, sr)
        cmd += ["-i", str(tmp_wav), "-c:a", "aac", "-b:a", "96k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-threads", "1",
            "-bitexact", "-map_metadata", "-1", str(path)]
    proc = subprocess.run(cmd, input=b"".join(f.astype(np.uint8).tobytes() for f in frames), capture_output=True)
    if tmp_wav.exists():
        tmp_wav.unlink()
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode()[:400])


def jump_edit(frames: list[np.ndarray], at: int, skip: int) -> list[np.ndarray]:
    """Remove ``skip`` frames at index ``at`` (a cut inside one shot)."""
    return frames[:at] + frames[at + skip:]


def duplicate_edit(frames: list[np.ndarray], at: int, repeat: int = 1) -> list[np.ndarray]:
    return frames[:at] + [frames[at - 1]] * repeat + frames[at:]

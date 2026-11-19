"""Band-limit check (§3.5): many TTS and voice-conversion outputs have a sharp cutoff well below Nyquist."""
from __future__ import annotations

import numpy as np
from scipy.signal import welch

from ... import config
from ..base import AnalysisContext, RawFinding, squash
from .common import load_native

ALTERNATIVES = ["Recorded or forwarded through a phone line or low-bitrate codec",
                "Resampled from a lower-quality source by the uploading app"]


def cutoff(y: np.ndarray, sr: int) -> dict | None:
    """Frequency above which the long-term spectrum collapses, and how sharply."""
    if len(y) < sr:
        return None
    f, p = welch(y, fs=sr, nperseg=4096, noverlap=2048)
    db = 10 * np.log10(p + 1e-14)
    ref = float(np.median(db[(f >= 500) & (f <= 4000)]))
    # smallest frequency above 3 kHz from which everything stays ≥ BANDLIMIT_DROP_DB below the speech band
    below = db < ref - config.BANDLIMIT_DROP_DB
    cand = np.where((f > 3000) & below)[0]
    for i in cand:
        if below[i:].mean() > 0.97:
            fc = float(f[i])
            # sharpness: dB lost over the 1 kHz just below the cutoff
            band = (f > fc - 1000) & (f <= fc)
            slope = float(db[band][0] - db[i]) if band.any() else 0.0
            return {"cutoff_hz": round(fc), "nyquist_hz": sr // 2, "drop_db": round(ref - float(np.median(db[i:])), 1),
                    "edge_db_per_khz": round(slope, 1)}
    return None


def run(ctx: AnalysisContext) -> list[RawFinding]:
    y, sr = load_native(ctx)
    if sr < 32000:
        ctx.log("audio", f"band-limit check skipped: source sample rate {sr} Hz is too low to tell")
        ctx.extra["bandlimit"] = {"skipped": f"sample rate {sr} Hz"}
        return []
    c = cutoff(y, sr)
    ctx.extra["bandlimit"] = c or {"cutoff_hz": None, "nyquist_hz": sr // 2}
    if not c or c["cutoff_hz"] > 0.8 * c["nyquist_hz"] or c["cutoff_hz"] >= 15000:
        return []   # codecs low-pass near 16 kHz routinely; only a much lower cutoff is unusual
    ratio = c["cutoff_hz"] / c["nyquist_hz"]
    return [RawFinding(
        indicator="band_limited", family="band_limit", name="Band-limited spectrum",
        location={"type": "time_range", "start": 0.0, "end": round(len(y) / sr, 2)},
        loc_label=f"Whole track · cutoff {c['cutoff_hz'] / 1000:.1f} kHz of {c['nyquist_hz'] / 1000:.1f} kHz",
        raw_score=squash((1 - ratio) * 10 + c["edge_db_per_khz"] / 10, mid=6.0, scale=1.5),
        method=f"Welch long-term spectrum at {sr} Hz: energy falls {c['drop_db']:.0f} dB below the 0.5–4 kHz band above "
               f"{c['cutoff_hz']} Hz (edge {c['edge_db_per_khz']:.0f} dB per kHz)",
        explanation=f"The recording has almost no energy above {c['cutoff_hz'] / 1000:.1f} kHz although the file could hold up to "
                    f"{c['nyquist_hz'] / 1000:.1f} kHz. Synthetic or converted speech is often generated at a lower rate and upsampled.",
        alternatives=ALTERNATIVES, sort=0.0, extra=c)]

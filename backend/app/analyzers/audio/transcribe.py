"""Transcript with word timestamps: faster-whisper ``base`` int8 on CPU (§3.5).

The model is loaded lazily from the local model folder and released after each file, so peak RAM
stays low. ``HF_HUB_OFFLINE`` is set, so a missing model fails fast instead of reaching the network.
"""
from __future__ import annotations

import gc
import os

from ... import config
from ..base import AnalysisContext, RawFinding
from .common import decode


def model_path() -> str:
    local = config.MODEL_DIR / f"faster-whisper-{config.WHISPER_MODEL}"
    return str(local) if local.exists() else config.WHISPER_MODEL


def transcribe(wav_path) -> dict:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from faster_whisper import WhisperModel

    model = WhisperModel(model_path(), device="cpu", compute_type=config.WHISPER_COMPUTE, cpu_threads=4,
                         download_root=str(config.MODEL_DIR))
    try:
        segments, info = model.transcribe(str(wav_path), beam_size=5, temperature=0.0, word_timestamps=True,
                                          vad_filter=False, condition_on_previous_text=False)
        segs = []
        for seg in segments:
            words = [{"w": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2),
                      "p": round(w.probability, 3)} for w in (seg.words or []) if w.word.strip()]
            segs.append({"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip(), "words": words})
        n_words = sum(len(s["words"]) for s in segs)
        mean_p = sum(w["p"] for s in segs for w in s["words"]) / n_words if n_words else 0.0
        return {"model": f"faster-whisper {config.WHISPER_MODEL} int8", "language": info.language,
                "segments": segs, "n_words": n_words, "mean_conf": round(mean_p, 3)}
    finally:
        del model
        gc.collect()


def run(ctx: AnalysisContext) -> list[RawFinding]:
    wav = decode(ctx.original, ctx.derived_dir / "audio_16k.wav", config.AUDIO_SR, config.MAX_AUDIO_SECONDS)
    tr = transcribe(wav)
    ctx.extra["transcript"] = tr
    ctx.shared.setdefault("transcripts", {})[ctx.label] = tr
    ctx.log("audio", f"transcript: {tr['n_words']} words · mean conf {tr['mean_conf']:.2f}")
    return []

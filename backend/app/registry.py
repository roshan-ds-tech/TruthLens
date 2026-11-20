"""All analyzers in run order, and the per-device analyzer settings."""
from __future__ import annotations

import importlib.util
from importlib import metadata as pkg_meta
from typing import Optional

from sqlmodel import Session

from . import config
from .analyzers import audio, deepfake, image, text, video
from .analyzers.base import FnAnalyzer
from .models import JsonMixin, Setting

ORDER = {
    "video": ["av_metadata", "frames", "frame_dupes", "optical_flow", "face_flicker", "frame_forensics", "ai_video"],
    "audio": ["av_metadata", "noise_floor", "band_limit", "prosody", "transcript", "ai_voice"],
    "image": ["exif", "ela", "noise", "jpeg_ghost", "copy_move", "ai_image"],
    "text": ["claims", "consistency", "ai_text"],
}
DEEPFAKE = [
    FnAnalyzer("ai_image", "AI-image detector", ("image",), deepfake.run_image, "AI-generated image detector",
               "Pretrained classifiers: camera photo vs image generator", "Smaug-AI-Image-Detector",
               optional_dep="transformers"),
    FnAnalyzer("ai_video", "AI-frames detector", ("video",), deepfake.run_video, "AI-generated video detector",
               "AI-image classifiers on sampled frames and face crops", "Smaug-AI-Image-Detector",
               optional_dep="transformers"),
    FnAnalyzer("ai_voice", "Voice-clone detector", ("audio",), deepfake.run_audio, "Synthetic voice detector",
               "wav2vec2 anti-spoofing: human speech vs TTS / voice cloning", "wav2vec2-large-xlsr",
               optional_dep="transformers"),
    FnAnalyzer("ai_text", "AI-text detector", ("text",), deepfake.run_text, "AI-written text detector",
               "ModernBERT classifier: human vs language-model writing", "ai-text-detector-modernbert",
               optional_dep="transformers"),
]
ALL: dict[str, FnAnalyzer] = {a.key: a for a in image.ANALYZERS + video.ANALYZERS + audio.ANALYZERS + text.ANALYZERS + DEEPFAKE}
DATA_STEPS = {"frames", "transcript", "claims"}   # produce data, not detections; failure is not a detector gap
# A missing learned detector leaves its AI estimate unavailable; editing indicators remain separate.
AI_STEPS = {"ai_image", "ai_video", "ai_voice", "ai_text"}


def steps_for(kind: str) -> list[FnAnalyzer]:
    return [ALL[k] for k in ORDER[kind]]


def dependency_available(a: FnAnalyzer) -> bool:
    return a.optional_dep is None or importlib.util.find_spec(a.optional_dep) is not None


def _key(user_id: Optional[int]) -> str:
    return "analyzers" if user_id is None else f"analyzers:{user_id}"


def enabled_map(s: Session, user_id: Optional[int] = None) -> dict[str, bool]:
    row = s.get(Setting, _key(user_id))
    stored = JsonMixin.loads(row.value_json, {}) if row else {}
    return {k: bool(stored.get(k, True)) for k in ALL}


def set_enabled(s: Session, updates: dict[str, bool], user_id: Optional[int] = None) -> dict[str, bool]:
    current = enabled_map(s, user_id)
    current.update({k: bool(v) for k, v in updates.items() if k in ALL})
    row = s.get(Setting, _key(user_id)) or Setting(key=_key(user_id), value_json="{}")
    row.value_json = JsonMixin.dumps(current)
    s.add(row)
    s.commit()
    return current


def investigator(s: Session) -> str:
    row = s.get(Setting, "investigator")
    return JsonMixin.loads(row.value_json, config.DEFAULT_INVESTIGATOR) if row else config.DEFAULT_INVESTIGATOR


def _pkg(name: str) -> str:
    try:
        return pkg_meta.version(name)
    except pkg_meta.PackageNotFoundError:
        return "not installed"


def versions() -> dict[str, str]:
    """Tool versions recorded in custody entries and shown in Settings."""
    return {"opencv": _pkg("opencv-python-headless"), "pillow": _pkg("pillow"), "numpy": _pkg("numpy"),
            "librosa": _pkg("librosa"), "faster-whisper": _pkg("faster-whisper"), "mediapipe": _pkg("mediapipe"),
            "sentence-transformers": _pkg("sentence-transformers"), "spacy": _pkg("spacy"), "scikit-learn": _pkg("scikit-learn")}

"""Learned deepfake detectors: is this image, video, voice or text AI-generated?

These complement the forensic analyzers (which find editing traces) with pretrained classifiers. Several candidate
checkpoints per modality can be downloaded; validation/run_deepfake_validation.py measures each one on labelled
real-vs-AI samples and records the best in validation/results/deepfake_calibration.json ("chosen"), which is what
runs here. Candidates, best first by default:

  image / video frames  abacusai/Smaug-AI-Image-Detector (Apache 2.0), umm-maybe/AI-image-detector (CC BY 4.0),
                        jacoballessio/ai-image-detect-distilled (MIT)
  voice                 Gustking/wav2vec2-large-xlsr-deepfake-audio-classification (Apache 2.0, XLS-R, ASVspoof2019),
                        mo-thecreator/Deepfake-audio-detection, MelodyMachine/Deepfake-audio-detection-V2 (Apache 2.0)
  text                  rasbt/ai-text-detector-modernbert (Apache 2.0, ModernBERT-base, 2026)

Each detector returns a raw score in [0, 1] (the model's probability for its AI / fake class). The scorer
calibrates it and combines it with the manipulation evidence. Models load from backend/models only (offline) and are
released after each item to keep peak RAM low.
"""
from __future__ import annotations

import gc
import os
from pathlib import Path

import numpy as np

from .. import config
from .base import AnalysisContext, RawFinding, fmt_t
from .base import isolated as _isolated

IMAGE_MODELS = ["smaug-ai-image-detector", "ai-image-detector", "ai-image-detect-distilled"]
AUDIO_MODELS = ["wav2vec2-large-xlsr-deepfake-audio-classification", "deepfake-audio-detection", "deepfake-audio-detection-v2"]
TEXT_MODELS = ["ai-text-detector-modernbert"]
SMAUG_CROP, SMAUG_SIDE, SMAUG_TOKENS = 528, 576, 140   # from the model card's reference code (must match training)
FAKE_WORDS = ("artificial", "fake", "ai", "generated", "synthetic", "spoof", "chatgpt", "machine", "gpt")
REAL_WORDS = ("human", "real", "bonafide", "bona-fide", "genuine", "authentic", "natural")
TEXT_MIN_WORDS = 40          # below this, text detectors are close to guessing


def model_dir(name: str) -> Path:
    return config.MODEL_DIR / name


def available(name: str) -> bool:
    d = model_dir(name)
    return d.exists() and (any(d.glob("*.safetensors")) or any(d.glob("*.bin"))) and not any(d.rglob("*.part"))


def chosen(kind: str, candidates: list[str]) -> list[str]:
    """The model(s) validation picked for this modality, else every available candidate in default order."""
    from ..scoring import deepfake as score

    pick = score.chosen_models(kind)
    use = [m for m in pick if available(m)] if pick else []
    return use or [m for m in candidates if available(m)][:1]


def fake_index(id2label: dict) -> int:
    """Which output is the AI / fake class, read from the model's own label names."""
    labels = {int(k): str(v).lower() for k, v in id2label.items()}
    for i, lab in labels.items():
        if any(w == lab or lab.startswith(w) or w in lab.split("_") for w in FAKE_WORDS) and not any(r in lab for r in REAL_WORDS):
            return i
    for i, lab in labels.items():
        if any(r in lab for r in REAL_WORDS):
            return 1 - i if len(labels) == 2 else i
    raise ValueError(f"cannot tell which label is 'fake' in {labels}")


def _offline():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


# ------------------------------------------------------------------ images

def image_scores(images: list, models: list[str] | None = None, crops: int = 3) -> dict[str, list[float]]:
    """P(AI-generated) per PIL image, per image model (default: the validated choice)."""
    _offline()
    import torch
    from transformers import AutoModelForImageClassification

    out: dict[str, list[float]] = {}
    for name in (models if models is not None else chosen("ai_image", IMAGE_MODELS)):
        if not available(name):
            continue
        if (model_dir(name) / "modules.json").exists():       # sentence-transformers checkpoint (Smaug)
            out[name] = _isolated(_smaug_scores, name, [im.convert("RGB") for im in images], crops)
            continue
        prep = _image_prep(name)
        model = AutoModelForImageClassification.from_pretrained(model_dir(name)).eval()
        k = fake_index(model.config.id2label)
        scores = []
        with torch.inference_mode():
            for i in range(0, len(images), 8):
                batch = torch.from_numpy(np.stack([prep(im) for im in images[i:i + 8]]))
                logits = model(pixel_values=batch).logits.float().numpy()
                scores += _softmax(logits)[:, k].tolist()
        out[name] = [round(float(s), 4) for s in scores]
        del model
        gc.collect()
    if not out:
        raise RuntimeError("no AI-image detector downloaded (run make setup)")
    return out


def _smaug_views(img, crops: int) -> list:
    """Shorter side to 576 px (upscaled to 528 if smaller), then 528 px crops at the start, centre and end of the
    long side (or the centre only), as in the Smaug model card's reference code (Apache 2.0)."""
    import math

    from PIL import Image, ImageOps

    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    if min(w, h) > SMAUG_SIDE:
        f = SMAUG_SIDE / min(w, h)
        img = img.resize((round(w * f), round(h * f)), Image.LANCZOS)
    elif min(w, h) < SMAUG_CROP:
        f = SMAUG_CROP / min(w, h)
        img = img.resize((math.ceil(w * f), math.ceil(h * f)), Image.BICUBIC)
    w, h = img.size
    C = SMAUG_CROP
    cx, cy = (w - C) // 2, (h - C) // 2
    if crops == 1:
        return [img.crop((cx, cy, cx + C, cy + C))]
    if w >= h:
        return [img.crop((x, cy, x + C, cy + C)) for x in (0, cx, w - C)]
    return [img.crop((cx, y, cx + C, y + C)) for y in (0, cy, h - C)]


def _float_except_vocab(model) -> None:
    """The checkpoint is stored in bfloat16, and bfloat16 inference is very slow on CPU. Convert to float32 module by
    module (never holding two full copies), but keep the 262k-token vocabulary table in bfloat16 and cast each lookup:
    image inputs use only a few of its rows. The results equal a plain float32 load; peak memory drops from about
    3.1 GB to about 1.6 GB."""
    import torch
    import torch.nn.functional as F

    for mod in model.modules():
        if isinstance(mod, torch.nn.Embedding) and mod.weight.numel() > 50_000_000:
            mod.weight.data = mod.weight.data.clone()   # own copy, so the memory-mapped checkpoint can be released
            scale = float(getattr(mod, "scalar_embed_scale", 1.0))
            mod.forward = lambda ids, m=mod, sc=scale: F.embedding(ids, m.weight, m.padding_idx).float() * sc
            continue
        for p in mod.parameters(recurse=False):
            p.data = p.data.float()
        for k, b in list(mod.named_buffers(recurse=False)):
            if b is not None and b.is_floating_point():
                mod._buffers[k] = b.float()


def _smaug_scores(name: str, images: list, crops: int) -> list[float]:
    import torch
    from sentence_transformers import SentenceTransformer

    st = SentenceTransformer(str(model_dir(name)), device="cpu", local_files_only=True,
                             config_kwargs={"audio_config": None}, model_kwargs={"torch_dtype": torch.bfloat16})
    _float_except_vocab(st)
    ip = st[0].processor.image_processor
    ip.max_soft_tokens = ip.image_seq_length = SMAUG_TOKENS
    out = []
    with torch.inference_mode():
        for i in range(0, len(images), 4):
            chunk = images[i:i + 4]
            flat = [{"image": v} for im in chunk for v in _smaug_views(im, crops)]
            logits = st.encode(flat, batch_size=1, convert_to_tensor=True).float().view(len(chunk), crops)
            out += torch.sigmoid(logits.mean(1)).tolist()
    del st
    gc.collect()
    return [round(float(p), 4) for p in out]


def _image_prep(name: str):
    """Resize / rescale / normalise exactly as the model's preprocessor_config.json says (the legacy
    ViTFeatureExtractor configs these models ship are no longer loadable by AutoImageProcessor)."""
    import json

    from PIL import Image

    cfg = json.loads((model_dir(name) / "preprocessor_config.json").read_text())
    size = cfg.get("size", 224)
    h, w = (size, size) if isinstance(size, int) else (size.get("height", size.get("shortest_edge", 224)),
                                                      size.get("width", size.get("shortest_edge", 224)))
    resample = int(cfg.get("resample", Image.BILINEAR))
    mean = np.array(cfg.get("image_mean", [0.5] * 3), np.float32)[:, None, None]
    std = np.array(cfg.get("image_std", [0.5] * 3), np.float32)[:, None, None]
    scale = float(cfg.get("rescale_factor", 1 / 255))

    def prep(im) -> np.ndarray:
        x = np.asarray(im.convert("RGB").resize((w, h), resample), np.float32).transpose(2, 0, 1) * scale
        return (x - mean) / std if cfg.get("do_normalize", True) else x

    return prep


def _ensemble(per_model: dict[str, list[float]]) -> list[float]:
    arr = np.array(list(per_model.values()))
    return [round(float(v), 4) for v in arr.mean(axis=0)]


def _r2(x: float) -> float:
    """Stored detector scores are rounded to 0.01 so float noise between CPUs cannot change a report."""
    return round(float(x), 2)


def run_image(ctx: AnalysisContext) -> list[RawFinding]:
    from PIL import Image, ImageOps

    with Image.open(ctx.original) as im:
        img = ImageOps.exif_transpose(im).convert("RGB")
    per = image_scores([img])
    raw = _r2(_ensemble(per)[0])
    ctx.extra["ai_detector"] = {"kind": "image", "raw": raw, "per_model": {k: _r2(v[0]) for k, v in per.items()},
                                "models": list(per)}
    return _finding(ctx, "ai_generated_image", "ai_image", "AI-generated image likelihood", raw,
                    {"type": "file", "field": "pixels"}, "Whole image",
                    f"Pretrained AI-image classifiers ({', '.join(per)}), averaged: {raw:.2f}",
                    "The image classifiers rate the picture as likely produced by an image generator rather than a camera.",
                    ["Heavily edited, filtered or upscaled real photo", "Generator styles the classifier was not trained on can go "
                     "either way", "Screenshots, renders and illustrations"])


def run_video(ctx: AnalysisContext) -> list[RawFinding]:
    """AI-image classifiers on evenly spaced frames, plus face crops when a face was tracked."""
    import cv2
    from PIL import Image

    cap = cv2.VideoCapture(str(ctx.original))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    picks = sorted({int(round(x)) for x in np.linspace(0, max(n - 1, 0), num=min(12, n))})
    frames, times = [], []
    for i in picks:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if ok:
            frames.append(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
            times.append(round(i / fps, 2))
    cap.release()
    if not frames:
        raise RuntimeError("no decodable frames")
    crops = []
    for t, x, y, w, h in (ctx.extra.get("face", {}).get("boxes") or [])[::4][:8]:
        k = int(np.argmin(np.abs(np.array(times) - t)))
        W, H = frames[k].size
        pad = 0.25
        box = (max(0, (x - pad * w) * W), max(0, (y - pad * h) * H), min(W, (x + w * (1 + pad)) * W), min(H, (y + h * (1 + pad)) * H))
        crops.append(frames[k].crop(tuple(int(v) for v in box)))
    per = image_scores(frames + crops, crops=1)
    scores = _ensemble(per)
    frame_scores, face_scores = scores[:len(frames)], scores[len(frames):]
    # Median over frames: a single frame can score high on heavily compressed or downscaled camera footage, so one
    # frame must not decide the clip. Face crops are small and upscaled, which the detector was not validated on;
    # they are shown but not counted.
    raw = _r2(np.median(frame_scores))
    ctx.extra["ai_detector"] = {"kind": "video", "raw": raw, "models": list(per),
                                "frames": [{"t": t, "p": _r2(p)} for t, p in zip(times, frame_scores)],
                                "faces": [_r2(p) for p in face_scores]}
    peak = times[int(np.argmax(frame_scores))]
    return _finding(ctx, "ai_generated_video", "ai_video", "AI-generated frames likelihood", raw,
                    {"type": "frame_range", "start": 0.0, "end": float(times[-1])},
                    f"{len(frames)} frames · most AI-like at {fmt_t(peak)}",
                    f"AI-image detector on {len(frames)} evenly spaced frames; median {raw:.2f}",
                    "Frames of this video look like the output of an image or video generator.",
                    ["Animation, CGI or heavy colour grading", "Strong compression or upscaling",
                     "Generators the classifier was not trained on can go either way"])


# ------------------------------------------------------------------ audio

def voice_scores(y: np.ndarray, sr: int, name: str | None = None) -> list[float]:
    names = [name] if name else chosen("ai_voice", AUDIO_MODELS)
    if not names:
        raise RuntimeError("voice deepfake detector not downloaded (run make setup)")
    return _isolated(_voice_scores, y, sr, names)


def _voice_scores(y: np.ndarray, sr: int, names: list[str]) -> list[float]:
    _offline()
    import torch
    from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

    fe = AutoFeatureExtractor.from_pretrained(model_dir(names[0]))
    model = AutoModelForAudioClassification.from_pretrained(model_dir(names[0])).eval()
    k = fake_index(model.config.id2label)
    target = getattr(fe, "sampling_rate", 16000)
    if sr != target:
        import librosa

        y = librosa.resample(y, orig_sr=sr, target_sr=target)
    win = 4 * target
    chunks = [y[i:i + win] for i in range(0, max(len(y), 1), win)][:30]
    chunks = [c for c in chunks if len(c) >= target] or [y]
    out = []
    with torch.inference_mode():
        for c in chunks:
            logits = model(**fe(c, sampling_rate=target, return_tensors="pt")).logits.float().numpy()
            out.append(round(float(_softmax(logits)[0, k]), 4))
    del model, fe
    gc.collect()
    return out


def run_audio(ctx: AnalysisContext) -> list[RawFinding]:
    from .audio.common import load_16k

    y, sr = load_16k(ctx)
    scores = voice_scores(y, sr)
    raw = _r2(np.median(scores))
    ctx.extra["ai_detector"] = {"kind": "audio", "raw": raw, "models": chosen("ai_voice", AUDIO_MODELS),
                                "chunks": [{"t": 4.0 * i, "p": _r2(p)} for i, p in enumerate(scores)]}
    return _finding(ctx, "synthetic_voice", "ai_voice", "Synthetic or cloned voice likelihood", raw,
                    {"type": "time_range", "start": 0.0, "end": round(len(y) / sr, 2)}, f"Whole track · {len(scores)} × 4 s windows",
                    f"wav2vec2 anti-spoofing classifier ({', '.join(chosen('ai_voice', AUDIO_MODELS))}) on {len(scores)} "
                    f"four-second windows; median {raw:.2f}",
                    "The voice classifier rates the speech as likely produced by text-to-speech or voice cloning.",
                    ["Heavy noise suppression or voice processing", "Low-quality phone or VoIP recordings",
                     "New cloning systems the classifier was not trained on can go either way"])


# ------------------------------------------------------------------ text

def text_scores(texts: list[str], name: str | None = None) -> list[float]:
    _offline()
    name = name or (chosen("ai_text", TEXT_MODELS) or [None])[0]
    if not name or not available(name):
        raise RuntimeError("AI-text detector not downloaded (run make setup)")
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_dir(name))
    model = AutoModelForSequenceClassification.from_pretrained(model_dir(name)).eval()
    k = fake_index(model.config.id2label)
    out = []
    with torch.inference_mode():
        for t in texts:
            enc = tok(t, truncation=True, max_length=512, return_tensors="pt")
            out.append(round(float(_softmax(model(**enc).logits.float().numpy())[0, k]), 4))
    del model, tok
    gc.collect()
    return out


def text_score(text: str) -> float:
    return text_scores([text])[0]


def run_text(ctx: AnalysisContext) -> list[RawFinding]:
    text = ctx.original.read_text("utf-8")
    words = len(text.split())
    raw = _r2(text_score(text))
    ctx.extra["ai_detector"] = {"kind": "text", "raw": raw, "models": chosen("ai_text", TEXT_MODELS), "words": words,
                                "short": words < TEXT_MIN_WORDS}
    return _finding(ctx, "ai_written_text", "ai_text", "AI-written text likelihood", raw,
                    {"type": "text_span", "start": 0, "end": len(text)}, f"Whole text · {words} words",
                    f"Transformer classifier for human vs language-model writing ({', '.join(chosen('ai_text', TEXT_MODELS))}): {raw:.2f}"
                    + (f"; only {words} words, so this is unreliable" if words < TEXT_MIN_WORDS else ""),
                    "The text classifier rates the writing as likely produced by a language model.",
                    ["Formal, templated or heavily edited human writing", "Non-native writers are flagged more often",
                     "Short texts give the classifier very little to go on"])


def _finding(ctx, indicator, family, name, raw, location, loc_label, method, explanation, alternatives) -> list[RawFinding]:
    """Only a likely-AI score becomes a finding; every score is kept for the deepfake assessment."""
    if raw < 0.5:
        return []
    return [RawFinding(indicator=indicator, family=family, name=name, location=location, loc_label=loc_label,
                       raw_score=raw, method=method, explanation=explanation, alternatives=alternatives, sort=0.0,
                       extra={"detector": True})]

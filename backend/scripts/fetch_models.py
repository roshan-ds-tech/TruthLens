"""Download the model files once (setup only). Analysis afterwards runs fully offline."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"


def whisper() -> None:
    dest = MODELS / "faster-whisper-base"
    if (dest / "model.bin").exists():
        print("whisper base: present")
        return
    from faster_whisper import download_model

    download_model("base", output_dir=str(dest))
    print("whisper base: downloaded")


def minilm() -> None:
    dest = MODELS / "all-MiniLM-L6-v2"
    if (dest / "model.safetensors").exists():
        print("MiniLM: present")
        return
    from huggingface_hub import snapshot_download

    snapshot_download("sentence-transformers/all-MiniLM-L6-v2", local_dir=str(dest),
                      allow_patterns=["*.json", "*.txt", "model.safetensors", "1_Pooling/*"])
    print("MiniLM: downloaded")


def face_landmarker() -> None:
    dest = MODELS / "face_landmarker.task"
    if dest.exists():
        print("face landmarker: present")
        return
    import urllib.request

    url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    urllib.request.urlretrieve(url, dest)
    print("face landmarker: downloaded")


def spacy_small() -> None:
    try:
        import en_core_web_sm  # noqa: F401
        print("spaCy en_core_web_sm: present")
    except ImportError:
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)


# Deepfake detectors (CPU, offline after this download, about 2.4 GB), all Apache 2.0. The detectors validation selected (validation/results/deepfake_calibration.json "models"). Older candidates that
# lost the comparison can be added with --candidates for re-running the comparison.
DETECTORS = {
    "smaug-ai-image-detector": ("abacusai/Smaug-AI-Image-Detector",
                                ["config.json", "config_sentence_transformers.json", "modules.json", "processor_config.json",
                                 "sentence_bert_config.json", "tokenizer.json", "tokenizer_config.json",
                                 "chat_template.jinja", "1_Pooling/config.json", "2_Normalize/config.json",
                                 "3_Dense/config.json", "3_Dense/model.safetensors", "model.safetensors"]),
    "wav2vec2-large-xlsr-deepfake-audio-classification": ("Gustking/wav2vec2-large-xlsr-deepfake-audio-classification",
                                                          ["config.json", "preprocessor_config.json", "model.safetensors"]),
    "ai-text-detector-modernbert": ("rasbt/ai-text-detector-modernbert",
                                    ["config.json", "tokenizer.json", "tokenizer_config.json", "model.safetensors"]),
}
CANDIDATES = {
    "ai-image-detector": ("umm-maybe/AI-image-detector", ["config.json", "preprocessor_config.json", "pytorch_model.bin"]),
    "ai-image-detect-distilled": ("jacoballessio/ai-image-detect-distilled",
                                  ["config.json", "preprocessor_config.json", "model.safetensors"]),
    "deepfake-audio-detection": ("mo-thecreator/Deepfake-audio-detection",
                                 ["config.json", "preprocessor_config.json", "model.safetensors"]),
    "deepfake-audio-detection-v2": ("MelodyMachine/Deepfake-audio-detection-V2",
                                    ["config.json", "preprocessor_config.json", "model.safetensors"]),
}


def detectors(candidates: bool = False) -> None:
    """Plain HTTPS downloads with resume (snapshot_download can stall on large files)."""
    import time
    import urllib.request

    for folder, (repo, files) in (DETECTORS | (CANDIDATES if candidates else {})).items():
        dest = MODELS / folder
        dest.mkdir(parents=True, exist_ok=True)
        for name in files:
            out, part = dest / name, dest / (name + ".part")
            out.parent.mkdir(parents=True, exist_ok=True)
            if out.exists():
                continue
            url = f"https://huggingface.co/{repo}/resolve/main/{name}"
            for attempt in range(8):
                try:
                    have = part.stat().st_size if part.exists() else 0
                    req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
                    with urllib.request.urlopen(req, timeout=60) as r, open(part, "ab" if have and r.status == 206 else "wb") as fh:
                        while chunk := r.read(1 << 20):
                            fh.write(chunk)
                    part.rename(out)
                    break
                except Exception as exc:  # noqa: BLE001 - retry and resume
                    print(f"{repo}/{name}: retry {attempt + 1} ({exc.__class__.__name__})")
                    time.sleep(3 + 3 * attempt)
            else:
                raise RuntimeError(f"could not download {repo}/{name}")
        print(f"{repo}: present")


if __name__ == "__main__":
    import sys

    MODELS.mkdir(parents=True, exist_ok=True)
    for step in (face_landmarker, spacy_small, whisper, minilm, detectors):
        try:
            step(candidates=True) if step is detectors and "--candidates" in sys.argv else step()
        except Exception as exc:  # report and continue: each model is optional for some analyzer
            print(f"{step.__name__}: FAILED {exc}")

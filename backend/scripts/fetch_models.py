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


if __name__ == "__main__":
    MODELS.mkdir(parents=True, exist_ok=True)
    for step in (face_landmarker, spacy_small, whisper, minilm):
        try:
            step()
        except Exception as exc:  # report and continue: each model is optional for some analyzer
            print(f"{step.__name__}: FAILED {exc}")

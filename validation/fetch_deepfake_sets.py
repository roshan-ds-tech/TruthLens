"""Download small labelled samples (real vs AI) used to calibrate and measure the deepfake detectors.

    python validation/fetch_deepfake_sets.py [--per-class 150]

Rows come from the Hugging Face datasets-server API, so only the sampled items are downloaded:
  * images: ComplexDataLab/OpenFake, config "core", split "test" (CC BY-NC 4.0); real photos vs many recent generators
  * audio:  SpeechAntiSpoofingBenchmarks/InTheWild (Apache 2.0); genuine vs cloned speech of the same public figures
  * text:   textsightai/ai-text-detection-benchmark-2026 (CC BY-SA 4.0); 2026 LLM text vs human text
Everything lands in validation/data/deepfake/ (git-ignored) with a manifest of sources and labels.
"""
from __future__ import annotations

import argparse
import io
import json
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "validation" / "data" / "deepfake"
API = "https://datasets-server.huggingface.co"


def get(url: str, tries: int = 8):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "truthlens-validation"}), timeout=90) as r:
                return r.read()
        except Exception as exc:  # the API is sometimes busy; back off and retry
            if k == tries - 1:
                raise
            print(f"  retry {k + 1}: {exc.__class__.__name__}")
            time.sleep(4 + 4 * k)


def rows(dataset: str, config: str, split: str, offset: int, length: int, where: str | None = None) -> list[dict]:
    q = {"dataset": dataset, "config": config, "split": split, "offset": offset, "length": length}
    if where:
        q["where"] = where
        url = f"{API}/filter?" + urllib.parse.urlencode(q)
    else:
        url = f"{API}/rows?" + urllib.parse.urlencode(q)
    return [r["row"] for r in json.loads(get(url))["rows"]]


def images(per_class: int, rng: random.Random) -> list[dict]:
    """Random pages of the test split (the filter endpoint is too slow on 2 M rows); real and AI kept balanced."""
    from PIL import Image

    d = OUT / "images"
    d.mkdir(parents=True, exist_ok=True)
    total = 91397
    items, got = [], {"real": 0, "fake": 0}
    offsets = [rng.randrange(0, total - 20) for _ in range(400)]
    for off in offsets:
        if min(got.values()) >= per_class:
            break
        try:
            page = rows("ComplexDataLab/OpenFake", "core", "test", off, 8)
        except Exception as exc:
            print(f"  skip page {off}: {exc}")
            continue
        for r in page:
            label = r.get("label")
            if label not in got or got[label] >= per_class:
                continue
            try:
                im = Image.open(io.BytesIO(get(r["image"]["src"]))).convert("RGB")
            except Exception:
                continue
            im.thumbnail((768, 768))
            name = f"{label}_{got[label]:03d}.jpg"
            im.save(d / name, "JPEG", quality=92)
            items.append({"path": f"images/{name}", "modality": "image", "label": label, "generator": r.get("model"),
                          "source": "ComplexDataLab/OpenFake core/test", "row_id": r.get("row_id")})
            got[label] += 1
        print(f"  images: {got}", flush=True)
    return items


def audio(per_class: int, rng: random.Random) -> list[dict]:
    """In-The-Wild (Mueller et al. 2022): genuine and cloned speech of the same public figures, same format for both
    classes. (garystafford/deepfake-audio-detection was dropped: every human clip there is 44.1 kHz stereo and every
    synthetic one 16 kHz mono, so the file format alone gives the label away.)"""
    ds = "SpeechAntiSpoofingBenchmarks/InTheWild"
    d = OUT / "audio"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.wav"):
        old.unlink()
    total = 31779
    items, got = [], {"real": 0, "fake": 0}
    for off in [rng.randrange(0, total - 10) for _ in range(600)]:
        if min(got.values()) >= per_class:
            break
        try:
            page = rows(ds, "default", "test", off, 6)
        except Exception as exc:
            print(f"  skip page {off}: {exc}")
            continue
        for r in page:
            label = "fake" if int(r["label"]) == 1 else "real"
            if got[label] >= per_class:
                continue
            src = r["audio"][0]["src"] if isinstance(r["audio"], list) else r["audio"]["src"]
            name = f"{label}_{got[label]:03d}.wav"
            (d / name).write_bytes(get(src))
            notes = json.loads(r.get("notes") or "{}")
            items.append({"path": f"audio/{name}", "modality": "audio", "label": label, "speaker": notes.get("speaker"),
                          "source": f"{ds} test ({r.get('path')})"})
            got[label] += 1
        print(f"  audio: {got}", flush=True)
    return items


def text(per_class: int, rng: random.Random) -> list[dict]:
    d = OUT / "text"
    d.mkdir(parents=True, exist_ok=True)
    items = []
    ai = rows("textsightai/ai-text-detection-benchmark-2026", "ai_generated_2026", "train", 0, 100)
    human = []
    for cfg in ("human_wikipedia_pre2022", "human_literature_publicdomain", "human_pmc_ccby_nonanglophone"):
        human += rows("textsightai/ai-text-detection-benchmark-2026", cfg, "train", 0, 100)
    rng.shuffle(human)
    for label, pool in (("fake", ai[:per_class]), ("real", human[:max(per_class, len(ai))])):
        for k, r in enumerate(pool):
            name = f"{label}_{k:03d}.txt"
            (d / name).write_text(r["text"], "utf-8")
            items.append({"path": f"text/{name}", "modality": "text", "label": label, "words": len(r["text"].split()),
                          "source": f"textsightai/ai-text-detection-benchmark-2026 ({r.get('source') or ''})"})
    print(f"  text: {sum(i['label'] == 'fake' for i in items)} AI, {sum(i['label'] == 'real' for i in items)} human")
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=150)
    ap.add_argument("--only", choices=["text", "audio", "images"], help="fetch one modality and merge it into the manifest")
    args = ap.parse_args()
    rng = random.Random(7)
    OUT.mkdir(parents=True, exist_ok=True)
    mf = OUT / "manifest.json"
    manifest = [m for m in json.loads(mf.read_text()) if m["modality"] != args.only.rstrip("s")] if args.only and mf.exists() else []
    for name, fn in (("text", text), ("audio", audio), ("images", images)):
        if args.only and name != args.only:
            continue
        print(f"Fetching {name}…")
        manifest += fn(args.per_class if name != "text" else 60, rng)
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(manifest)} items → {OUT}")


if __name__ == "__main__":
    main()

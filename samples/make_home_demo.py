"""Build the Home page's live preview: a short press-briefing clip with a known edit, analysed by TruthLens.

Writes public/media/home-demo.mp4 and public/media/home-demo.json. The JSON holds the analyzer's real output
for this clip (findings, rule, verdict, transcript words, waveform, suspicion curve); the Home page only replays
it in time with the video. Needs macOS `say` to regenerate; the outputs are committed.

Ground truth: 10 frames are cut at 8.0 s, and the speech after 8.2 s was recorded in a different (noisier) room.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "validation"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import synth  # noqa: E402

OUT = ROOT / "public" / "media"
SR, FPS = 16000, 25
W, H = 960, 540
CUT_FRAME, CUT_LEN = 200, 10          # 10 frames removed at 8.0 s
SPLICE_S, TOTAL_S = 8.2, 16.0
PART_A = "Good evening, everyone. Thank you for joining at short notice. The state has seen heavy rain this week."
PART_B = "The government has decided to declare a three day holiday from tomorrow. Schools and offices will remain closed."


def tts(text: str, seconds: float) -> np.ndarray:
    if shutil.which("say") is None:
        raise SystemExit("macOS `say` is needed to regenerate the speech; the committed media can be used as is.")
    import soundfile as sf

    with tempfile.TemporaryDirectory() as tmp:
        aiff, wav = Path(tmp) / "s.aiff", Path(tmp) / "s.wav"
        subprocess.run(["say", "-v", "Rishi", "-r", "175", "-o", str(aiff), text], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff), "-ar", str(SR), "-ac", "1", str(wav)], check=True)
        y, _ = sf.read(wav, dtype="float32")
    n = int(seconds * SR)
    y = np.pad(y, (int(0.25 * SR), 0))
    print(f"  speech {len(y) / SR:.1f} s for a {seconds:.1f} s slot")
    return np.pad(y, (0, max(0, n - len(y))))[:n]


def frames() -> list[np.ndarray]:
    """A slow push-in with a little drift across the briefing-room photo: one continuous shot."""
    with Image.open(ROOT / "public" / "img" / "press-briefing.jpg") as im:
        src = np.asarray(im.convert("RGB"))
    h, w = src.shape[:2]
    n = int(TOTAL_S * FPS) + CUT_LEN
    out = []
    for i in range(n):
        u = i / (n - 1)
        scale = 1.0 + 0.16 * u
        cw, ch = w / scale, h / scale
        cx = w / 2 + 40 * np.sin(u * np.pi) - 20 * u
        cy = h / 2 + 12 * np.cos(u * 2 * np.pi)
        m = np.float32([[W / cw, 0, -(cx - cw / 2) * W / cw], [0, H / ch, -(cy - ch / 2) * H / ch]])
        out.append(cv2.warpAffine(src, m, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT))
    return synth.jump_edit(out, CUT_FRAME, CUT_LEN)


def analyse(clip: Path) -> dict:
    from app import config, db, pipeline
    from app.api import adapters
    from app.api.routes import graph_for
    from app.ingest.service import ingest_file
    from app.models import Case, Evidence, JsonMixin

    config.set_data_dir(tempfile.mkdtemp(prefix="tl-home-"))
    db.reset_engine()
    with db.session() as s:
        case = Case(id="C-0007", title="Viral clip: minister announces holiday", investigator="TruthLens demo")
        s.add(case)
        s.commit()
        ingest_file(s, case, clip, "press_briefing_clip.mp4", "TruthLens demo")
        pipeline.run_case(s, case.id, None, "TruthLens demo")
        s.refresh(case)
        detail = adapters.case_detail(s, case)
        findings = adapters.case_findings(s, case.id)
        rules = graph_for(s, case)["rules"]
        from sqlmodel import select

        extra = {e.kind: JsonMixin.loads(e.extra_json, {}) for e in s.exec(select(Evidence))}
    tr = extra.get("audio", {}).get("transcript", {})
    return {
        "generated_by": "samples/make_home_demo.py (TruthLens analysis of this exact clip)",
        "ground_truth": {"video_cut_s": CUT_FRAME / FPS, "audio_splice_s": SPLICE_S},
        "duration": round(len(frames_cache) / FPS, 2),
        "fps": FPS,
        "verdict": {k: detail["verdict"][k] for k in ("key", "label", "lo", "hi", "why")},
        "findings": [{"id": f["finding_id"], "modality": f["modality"], "name": f["name"], "loc": f["loc_label"],
                      "start": f["location"].get("start"), "end": f["location"].get("end"), "lo": f["conf_low"],
                      "hi": f["conf_high"], "key": f["verdict"]["key"], "label": f["verdict"]["label"],
                      "explanation": f["explanation"]} for f in findings],
        "rules": [{"id": r["id"], "name": r["name"], "links": r["links"], "tag": r["tag"]} for r in rules],
        "waveform": extra.get("audio", {}).get("waveform", {}).get("peaks", []),
        "curve": extra.get("video", {}).get("suspicion_curve", []),
        "words": [w for seg in tr.get("segments", []) for w in seg.get("words", [])],
    }


frames_cache: list[np.ndarray] = []


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    a = tts(PART_A, SPLICE_S) * 0.85 + synth.room_noise(int(SPLICE_S * SR), 31, -55.0, 0.6)
    b = tts(PART_B, TOTAL_S - SPLICE_S) * 0.85 + synth.room_noise(int((TOTAL_S - SPLICE_S) * SR), 32, -44.0, 0.9)
    audio = np.clip(np.concatenate([a, b]), -1, 1).astype(np.float32)
    frames_cache.extend(frames())
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "clip.mp4"
        synth.write_video(raw, frames_cache, FPS, audio, SR)
        final = OUT / "home-demo.mp4"
        # web delivery: moov atom first so it starts playing before it has fully downloaded
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-c:v", "libx264", "-crf", "27", "-preset", "slow",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(final)], check=True)
    data = analyse(final)
    (OUT / "home-demo.json").write_text(json.dumps(data, indent=1))
    print(f"{final.name}: {final.stat().st_size / 1e6:.2f} MB · {data['duration']} s · verdict {data['verdict']['label']} "
          f"{data['verdict']['lo']}–{data['verdict']['hi']}")
    for f in data["findings"]:
        print(f"  {f['id']:10s} {f['label']:28s} {f['lo']:.2f}–{f['hi']:.2f}  {f['name']} · {f['loc']}")
    print("  rules:", ", ".join(r["id"] for r in data["rules"]) or "none", "· words:", len(data["words"]))


if __name__ == "__main__":
    main()

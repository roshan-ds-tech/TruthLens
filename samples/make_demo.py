"""Build the demo case from the design doc walkthrough (§4) into samples/demo_case/.

The files are committed, so `make demo` works without regenerating them. Regenerating needs macOS
`say` for the speech; everything else is seeded and deterministic.

Ground truth (what the analysis should find):
  * clip.mp4: a cut at 14.0 s (12 frames removed inside one shot)
  * its audio: speech recorded in two rooms; background noise steps up ~9 dB at 14.2 s
  * podium_photo.jpg: EXIF Software "Adobe Photoshop", DateTimeOriginal 2024-03-03, stale thumbnail
  * caption.txt: dated 12 Nov 2026 (conflicts with the photo's EXIF date)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "validation"))
import synth  # noqa: E402

OUT = ROOT / "samples" / "demo_case"
SR = 16000
FPS = 25
PART_A = ("Good evening, everyone. Thank you for joining at short notice. As you know, the state has seen heavy rain "
          "this week, and our teams are on the ground.")
PART_B = ("The government has decided to declare a three day holiday from tomorrow. All schools and offices will remain "
          "closed during this period.")
CAPTION = ("BREAKING: Minister announces 3-day state holiday from tomorrow. The minister said \"the government has decided "
           "to declare a three day holiday from tomorrow\". Schools and offices closed. Forward to all groups. — 12 Nov 2026")


def tts(text: str, voice: str, seconds: float) -> np.ndarray:
    if shutil.which("say") is None:
        raise SystemExit("macOS `say` is needed to regenerate the demo speech; the committed files can be used as they are.")
    import soundfile as sf

    with tempfile.TemporaryDirectory() as tmp:
        aiff, wav = Path(tmp) / "s.aiff", Path(tmp) / "s.wav"
        subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff), "-ar", str(SR), "-ac", "1", str(wav)], check=True)
        y, _ = sf.read(wav, dtype="float32")
    n = int(seconds * SR)
    return np.pad(y, (0, max(0, n - len(y))))[:n]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)
    photos = dict(synth.photos())

    # audio: two "rooms" joined at 14.2 s
    cut_s, total_s = 14.2, 25.0
    a = tts(PART_A, "Rishi", cut_s) * 0.8 + synth.room_noise(int(cut_s * SR), 1, -56.0, 0.6)
    b = tts(PART_B, "Rishi", total_s - cut_s) * 0.8 + synth.room_noise(int((total_s - cut_s) * SR), 2, -47.0, 0.9)
    audio = np.clip(np.concatenate([a, b]), -1, 1).astype(np.float32)

    # video: one continuous shot with 12 frames cut at 14.0 s; total length matches the audio
    frames = synth.pan_frames(synth.crops(photos["astronaut"], 384, 1, rng)[0], total_s + 12 / FPS, FPS, (640, 360), seed=11)
    frames = synth.jump_edit(frames, int(14.0 * FPS), 12)
    synth.write_video(OUT / "clip.mp4", frames, FPS, audio, SR)

    # still photo with an editor tag, an old capture date and a thumbnail from before the edit
    base = synth.crops(photos["coffee"], 384, 1, rng)[0]
    exif = {"Make": "samsung", "Model": "SM-A525F", "Software": "Adobe Photoshop 25.1 (Windows)",
            "DateTimeOriginal": "2024:03:03 10:41:22", "DateTime": "2026:11:12 21:36:04"}
    other = synth.crops(photos["chelsea"], 384, 1, rng)[0]
    (OUT / "podium_photo.jpg").write_bytes(synth.jpeg(base, 90, exif, thumb=other))
    (OUT / "caption.txt").write_text(CAPTION + "\n", "utf-8")
    (OUT / "README.md").write_text(__doc__.strip() + "\n", "utf-8")
    (OUT / "ground_truth.json").write_text(json.dumps({
        "video_cut_s": 14.0, "audio_splice_s": cut_s, "photo_exif_date": "2024-03-03", "caption_date": "2026-11-12"}, indent=2))
    for p in sorted(OUT.iterdir()):
        print(f"{p.name:20s} {p.stat().st_size:>9d}")


if __name__ == "__main__":
    main()

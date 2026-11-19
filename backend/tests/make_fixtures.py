"""Regenerate the small test fixtures in tests/fixtures/ (deterministic; committed to the repo)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "validation"))
import synth  # noqa: E402

OUT = Path(__file__).parent / "fixtures"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rng = np.random.default_rng(7)
    photos = dict(synth.photos())
    base = synth.crops(photos["coffee"], 384, 1, rng)[0]
    donor = synth.crops(photos["chelsea"], 256, 1, rng)[0]

    (OUT / "image_clean.jpg").write_bytes(synth.jpeg(base, 92, synth.CAMERA_EXIF))
    t = synth.splice(base, donor, np.random.default_rng(1), base_q=70, final_q=95, frac=0.12)
    (OUT / "image_spliced.jpg").write_bytes(t.data)
    np.save(OUT / "image_spliced_mask.npy", t.mask)
    rocket = synth.crops(photos["rocket"], 384, 1, rng)[0]
    t = synth.copy_move(rocket, np.random.default_rng(3), base_q=90, final_q=92, frac=0.05)
    (OUT / "image_copymove.jpg").write_bytes(t.data)
    np.save(OUT / "image_copymove_mask.npy", t.mask)
    edited_exif = {"Make": "samsung", "Model": "SM-A525F", "Software": "Adobe Photoshop 25.1 (Windows)",
                   "DateTimeOriginal": "2024:03:03 10:41:22", "DateTime": "2026:11:12 21:36:04"}
    other = synth.crops(photos["astronaut"], 384, 1, rng)[0]
    (OUT / "image_exif_edited.jpg").write_bytes(synth.jpeg(base, 90, edited_exif, thumb=other))

    sr = 16000
    synth.write_wav(OUT / "audio_clean.wav", synth.recording(8.0, 11, sr), sr)
    synth.write_wav(OUT / "audio_spliced.wav", synth.spliced_recording(8.0, 4.2, 12, sr), sr)
    low = synth.recording(6.0, 13, 8000)
    synth.write_wav(OUT / "audio_bandlimited.wav", synth.band_limited(low, 8000, 44100), 44100)

    frames = synth.pan_frames(synth.crops(photos["astronaut"], 384, 1, rng)[0], 6.0, 25, (320, 240), seed=2)
    synth.write_video(OUT / "video_clean.mp4", frames, 25)
    edited = synth.duplicate_edit(synth.jump_edit(frames, 75, 14), 110, 1)
    synth.write_video(OUT / "video_jump.mp4", edited, 25)

    (OUT / "caption.txt").write_text("BREAKING: Minister announces 3-day state holiday from tomorrow. "
                                     "Schools and offices closed. Forward to all groups. — 12 Nov 2026\n", "utf-8")
    (OUT / "corrupt.jpg").write_bytes(b"\xff\xd8\xff\xe0" + bytes(range(256)) * 4)
    (OUT / "unsupported.bin").write_bytes(b"\x7fELF" + bytes(200))
    for p in sorted(OUT.iterdir()):
        print(f"{p.name:28s} {p.stat().st_size:>8d}")


if __name__ == "__main__":
    main()

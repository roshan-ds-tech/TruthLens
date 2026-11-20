"""One test group per analyzer, on small deterministic fixtures (see make_fixtures.py)."""
import numpy as np
import pytest

from conftest import FIXTURES, iou, make_ctx


def _run(key, name, kind):
    from app import registry

    ctx = make_ctx(FIXTURES / name, kind)
    if kind == "video":
        for pre in ("frames", "frame_dupes", "optical_flow"):
            if pre == key:
                break
            registry.ALL[pre].run(ctx)
    return registry.ALL[key].run(ctx), ctx


# ---------------------------------------------------------------- image

@pytest.mark.parametrize("key", ["ela", "noise", "jpeg_ghost", "copy_move", "exif"])
def test_image_clean_has_no_strong_signal(key):
    findings, _ = _run(key, "image_clean.jpg", "image")
    assert all(f.raw_score < 0.7 for f in findings), [(f.indicator, f.raw_score) for f in findings]


def test_image_splice_localised():
    mask = np.load(FIXTURES / "image_spliced_mask.npy")
    found = []
    for key in ("ela", "jpeg_ghost", "noise"):
        fs, ctx = _run(key, "image_spliced.jpg", "image")
        found += fs
        assert (ctx.artifact_dir / f"{'ghost' if key == 'jpeg_ghost' else key}.png").exists()
    best = max((iou(f.location, mask) for f in found if f.location["type"] == "bbox"), default=0)
    assert best > 0.3, f"no region overlaps the pasted patch (best IoU {best:.2f})"


def test_copy_move_found():
    fs, ctx = _run("copy_move", "image_copymove.jpg", "image")
    assert fs and fs[0].indicator == "copy_move" and fs[0].extra["inliers"] >= 12
    assert "pair" in fs[0].location
    assert (ctx.artifact_dir / "copymove.png").exists()


def test_exif_rules():
    fs, _ = _run("exif", "image_exif_edited.jpg", "image")
    kinds = {f.indicator for f in fs}
    assert {"editor_software_tag", "modified_after_capture", "thumbnail_mismatch"} <= kinds
    clean, ctx = _run("exif", "image_clean.jpg", "image")
    assert clean == []


# ---------------------------------------------------------------- audio

def test_audio_splice_timestamp():
    fs, ctx = _run("noise_floor", "audio_spliced.wav", "audio")
    assert fs, "splice not found"
    assert min(abs(f.location["start"] - 4.2) for f in fs) < 0.25
    assert (ctx.artifact_dir / "spectrogram.png").exists() and len(ctx.extra["waveform"]["peaks"]) == 140


def test_audio_clean_no_splice():
    fs, _ = _run("noise_floor", "audio_clean.wav", "audio")
    assert fs == []


def test_band_limit():
    fs, _ = _run("band_limit", "audio_bandlimited.wav", "audio")
    assert fs and fs[0].indicator == "band_limited" and fs[0].extra["cutoff_hz"] < 6000
    # a 16 kHz file cannot be checked and must say so rather than flag
    fs, ctx = _run("band_limit", "audio_clean.wav", "audio")
    assert fs == [] and "skipped" in ctx.extra["bandlimit"]


def test_prosody_runs():
    pytest.importorskip("librosa")
    fs, ctx = _run("prosody", "audio_clean.wav", "audio")
    assert "f0_cv" in ctx.extra["prosody"] or "note" in ctx.extra["prosody"]
    assert all(f.raw_score <= 0.45 for f in fs), "prosody is a weak indicator only"


def test_transcript_when_model_present():
    from app import config

    if not (config.MODEL_DIR / "faster-whisper-base" / "model.bin").exists():
        pytest.skip("whisper model not downloaded (make setup)")
    fs, ctx = _run("transcript", "audio_clean.wav", "audio")
    assert "segments" in ctx.extra["transcript"]


# ---------------------------------------------------------------- video

def test_video_clean_no_findings():
    from app import registry

    ctx = make_ctx(FIXTURES / "video_clean.mp4", "video")
    found = []
    for key in ("frames", "frame_dupes", "optical_flow"):
        found += registry.ALL[key].run(ctx)
    assert found == []


def test_video_jump_and_duplicate():
    from app import registry

    ctx = make_ctx(FIXTURES / "video_jump.mp4", "video")
    found = []
    for key in ("frames", "frame_dupes", "optical_flow"):
        found += registry.ALL[key].run(ctx)
    flow = [f for f in found if f.indicator == "flow_discontinuity"]
    dup = [f for f in found if f.indicator == "duplicate_frames"]
    assert flow and abs(flow[0].location["start"] - 2.96) < 0.1, [f.loc_label for f in flow]
    assert dup and dup[0].location["frames"][0] == 110
    from app.analyzers.video import suspicion_curve

    curve = suspicion_curve(ctx, found)
    assert len(curve) >= 5 and max(curve) == pytest.approx(max(curve[2], curve[3], curve[4]))


def test_face_flicker_runs_without_face():
    from app import config

    if not (config.MODEL_DIR / "face_landmarker.task").exists():
        pytest.skip("face landmarker model not downloaded")
    fs, ctx = _run("face_flicker", "video_clean.mp4", "video")
    assert fs == [] and ctx.extra["face"]["frames_with_face"] >= 0


# ---------------------------------------------------------------- text

def test_claims_extraction():
    from app.analyzers.text.claims import extract

    claims = extract((FIXTURES / "caption.txt").read_text())
    kinds = {c.kind for c in claims}
    assert {"date", "number", "quote"} <= kinds
    date = next(c for c in claims if c.kind == "date" and not c.relative)
    assert date.value == "2026-11-12"


def test_caption_date_conflict_with_exif():
    from app.analyzers.text import consistency

    text_ctx = make_ctx(FIXTURES / "caption.txt", "text", label="E-02")
    img_ctx = make_ctx(FIXTURES / "image_exif_edited.jpg", "image", label="E-01")
    text_ctx.case_evidence = [img_ctx, text_ctx]
    fs = consistency.run(text_ctx)
    conflict = [f for f in fs if f.indicator == "claim_date_conflict"]
    assert conflict and conflict[0].extra["target_evidence"] == "E-01"
    assert conflict[0].extra["compare"][1]["v"] == "03 Mar 2024"
    statuses = {c["kind"]: c["status"] for c in text_ctx.extra["claims"]}
    assert statuses["date"] == "conflict"


def test_caption_consistent_date_is_not_flagged():
    from app.analyzers.text import consistency

    text_ctx = make_ctx(FIXTURES / "caption.txt", "text", label="E-02")
    img_ctx = make_ctx(FIXTURES / "image_clean.jpg", "image", label="E-01")   # EXIF 12 Nov 2026
    text_ctx.case_evidence = [img_ctx, text_ctx]
    assert [f for f in consistency.run(text_ctx) if f.indicator == "claim_date_conflict"] == []


def test_similarity_backend_works():
    from app.analyzers.text.consistency import similarities

    sims = similarities("declare a three day holiday", ["the government will declare a three day holiday", "rain in the city"])
    assert sims[0] > sims[1]


def test_shot_change_is_not_a_motion_break(tmp_path):
    """Two different shots edited together is ordinary editing; only a jump inside one shot is a finding."""
    import synth
    from app import registry

    photos = dict(synth.photos())
    a = synth.pan_frames(photos["coffee"], 3.0, 25, (320, 240), seed=1)
    b = synth.pan_frames(photos["rocket"], 3.0, 25, (320, 240), seed=2)
    p = tmp_path / "two_shots.mp4"
    synth.write_video(p, a + synth.jump_edit(b, 30, 12), 25)
    ctx = make_ctx(p, "video", tmp_path)
    found = []
    for key in ("frames", "frame_dupes", "optical_flow"):
        found += registry.ALL[key].run(ctx)
    flows = [f for f in found if f.indicator == "flow_discontinuity"]
    assert len(flows) == 1 and abs(flows[0].location["start"] - (3.0 + 29 / 25)) < 0.1, [f.loc_label for f in flows]
    assert any(abs(c - 3.0) < 0.1 for c in ctx.extra["cuts"]), "the shot change is recorded as a cut"


def test_startup_motion_is_not_a_splice_but_an_interior_jump_is(monkeypatch):
    from app.analyzers.video import flow_jumps
    from types import SimpleNamespace
    rng = np.random.default_rng(7)
    frame = rng.integers(0, 255, (36, 64), dtype=np.uint8)
    frames = {"gray": [frame.copy() for _ in range(25)], "t": np.arange(25) / 25,
              "hist": [np.ones(32, np.float32)] * 25}
    magnitudes = np.ones(25); magnitudes[0] = 0; magnitudes[1] = 20; magnitudes[12] = 20
    monkeypatch.setattr(flow_jumps, "decode", lambda ctx: frames)
    monkeypatch.setattr(flow_jumps, "flow_series", lambda gray: magnitudes)
    ctx = SimpleNamespace(extra={}, log=lambda *args: None)
    findings = flow_jumps.run(ctx)
    assert len(findings) == 1 and findings[0].location["frames"] == [11, 12]

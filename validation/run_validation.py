"""Build the seeded test set, run the analyzers, and write results/metrics.json + results/calibration.json.

    python validation/run_validation.py [--quick]

Everything is generated from fixed seeds (see synth.py) and labelled "small self-made test set".
Metrics are per indicator: detection rate (localised hits on tampered items), false-positive rate on
untouched items, finding-level precision, image IoU, splice timestamp error, and a reliability table
built from 5-fold cross-validated Platt calibration (so it is not scored on its own training data).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "validation"))

import synth  # noqa: E402
from app import config, registry  # noqa: E402
from app.analyzers.base import AnalysisContext  # noqa: E402
from app.analyzers.text import consistency  # noqa: E402
from app.ingest.metadata import av_metadata, image_metadata  # noqa: E402

DATA = ROOT / "validation" / "data"
RESULTS = ROOT / "validation" / "results"
SEED = 7
VERSION = "v1.0"

INDICATOR_INFO = {
    "ela_inconsistency": ("Error level inconsistency", "image", "image"),
    "noise_inconsistency": ("Noise map discontinuity", "image", "grain"),
    "jpeg_ghost": ("JPEG ghost", "image", "layers"),
    "copy_move": ("Copy-move match", "image", "content_copy"),
    "editor_software_tag": ("Editing software tag", "image", "data_object"),
    "thumbnail_mismatch": ("Thumbnail mismatch", "image", "photo_size_select_small"),
    "noise_floor_step": ("Noise-floor step", "audio", "graphic_eq"),
    "band_limited": ("Band-limited spectrum", "audio", "equalizer"),
    "uniform_prosody": ("Uniform prosody", "audio", "record_voice_over"),
    "flow_discontinuity": ("Optical-flow discontinuity", "video", "movie"),
    "duplicate_frames": ("Duplicated frame", "video", "filter_none"),
    "claim_date_conflict": ("Date conflict", "text", "notes"),
    "claim_speech_mismatch": ("Quote not in speech", "text", "subtitles"),
}
# which tampering each indicator is meant to catch (detection rate is computed on these items only)
TARGETS = {
    "ela_inconsistency": {"splice", "retouch"}, "noise_inconsistency": {"splice", "retouch"}, "jpeg_ghost": {"splice"},
    "copy_move": {"copy_move"}, "editor_software_tag": {"exif_edit"}, "thumbnail_mismatch": {"exif_edit"},
    "noise_floor_step": {"audio_splice"}, "band_limited": {"tts", "upsampled"}, "uniform_prosody": {"tts"},
    "flow_discontinuity": {"video_jump"}, "duplicate_frames": {"video_duplicate"},
    "claim_date_conflict": {"date_conflict"}, "claim_speech_mismatch": {"speech_mismatch"},
}
FP_CAUSE = {
    "ela_inconsistency": "Sharp edges and text recompress with more error",
    "noise_inconsistency": "Mixed focus and flat areas change visible noise",
    "jpeg_ghost": "Flat areas give uninformative re-save curves",
    "copy_move": "Repeating texture matches itself",
    "noise_floor_step": "Background noise source starting or stopping",
    "band_limited": "Low-bitrate or phone-band recording",
    "uniform_prosody": "Monotone delivery",
    "flow_discontinuity": "Sudden camera movement",
    "duplicate_frames": "Frame-rate conversion",
    "claim_date_conflict": "Camera clock wrong",
    "claim_speech_mismatch": "Loose paraphrase in the caption",
}


def ctx_for(path: Path, kind: str, work: Path, label: str = "E-01") -> AnalysisContext:
    meta = image_metadata(path) if kind == "image" else av_metadata(path) if kind in ("audio", "video") else {}
    return AnalysisContext("VAL", 0, label, kind, path.name, "", path, work / "d", work / "a", meta, lambda a, b: None)


def run_steps(ctx: AnalysisContext, keys: list[str]) -> list:
    out = []
    for k in keys:
        out += registry.ALL[k].run(ctx)
    return out


# ------------------------------------------------------------------ dataset builders

def build_images(n_per: int, rng: np.random.Generator) -> list[dict]:
    d = DATA / "images"
    d.mkdir(parents=True, exist_ok=True)
    photos = synth.photos()
    bases = []
    for name, rgb in photos:
        for i, c in enumerate(synth.crops(rgb, 384, max(2, n_per // 3), rng)):
            bases.append((f"{name}_{i}", c))
    rng.shuffle(bases)
    items = []

    def save(name: str, data: bytes, kind: str, neg_type: str | None = None, mask=None, params=None):
        p = d / f"{name}.jpg"
        p.write_bytes(data)
        if mask is not None:
            np.save(d / f"{name}_mask.npy", mask)
        items.append({"path": str(p), "modality": "image", "kind": kind, "neg_type": neg_type,
                      "mask": str(d / f"{name}_mask.npy") if mask is not None else None, "params": params or {}})

    k = 0
    for name, base in bases[:n_per]:
        save(f"clean_cam_{k}", synth.jpeg(base, int(rng.choice([90, 92, 95])), synth.CAMERA_EXIF), "clean", "Camera JPEG with EXIF")
        k += 1
    for name, base in bases[n_per:n_per + n_per // 2]:
        save(f"clean_wa_{k}", synth.jpeg(synth.jpeg_rgb(base, 92), int(rng.choice([70, 75, 80]))), "clean", "Recompressed JPEG, EXIF stripped")
        k += 1
    pool = bases + bases
    for i in range(n_per):
        _, base = pool[i]
        _, donor = pool[i + 5]
        t = synth.splice(base, donor, rng, int(rng.choice([60, 70, 80])), int(rng.choice([90, 95])), float(rng.uniform(0.05, 0.14)))
        save(f"splice_{i}", t.data, "splice", mask=t.mask, params=t.params)
    for i in range(n_per // 2):
        t = synth.copy_move(pool[i + 3][1], rng, 90, int(rng.choice([90, 95])), float(rng.uniform(0.03, 0.07)))
        save(f"copymove_{i}", t.data, "copy_move", mask=t.mask, params=t.params)
    for i in range(n_per // 2):
        t = synth.retouch(pool[i + 7][1], rng, int(rng.choice([70, 80])), 95)
        save(f"retouch_{i}", t.data, "retouch", mask=t.mask, params=t.params)
    for i in range(n_per // 3):
        _, base = pool[i + 11]
        other = pool[i + 13][1]
        ex = dict(synth.CAMERA_EXIF, Software="Adobe Photoshop 25.1 (Windows)", DateTime="2026:11:12 21:36:04",
                  DateTimeOriginal="2024:03:03 10:41:22")
        save(f"exifedit_{i}", synth.jpeg(base, 90, ex, thumb=other), "exif_edit")
    return items


def build_audio(n_per: int, rng: np.random.Generator) -> list[dict]:
    d = DATA / "audio"
    d.mkdir(parents=True, exist_ok=True)
    items = []
    for i in range(n_per):
        y = synth.recording(10.0, 300 + i, 16000, float(rng.uniform(-60, -44)), float(rng.uniform(0.4, 0.9)))
        p = d / f"clean_{i}.wav"
        synth.write_wav(p, y, 16000)
        items.append({"path": str(p), "modality": "audio", "kind": "clean", "neg_type": "Clean recording (synthetic voice)"})
    for i in range(n_per):
        cut = float(rng.uniform(3.0, 7.0))
        step = float(rng.choice([-1, 1]) * rng.uniform(6.0, 14.0))
        y = synth.spliced_recording(10.0, cut, 500 + i, 16000, abs(step)) if step > 0 else \
            synth.spliced_recording(10.0, cut, 500 + i, 16000, abs(step))[::-1].copy()
        truth = cut if step > 0 else 10.0 - cut
        p = d / f"splice_{i}.wav"
        synth.write_wav(p, y, 16000)
        items.append({"path": str(p), "modality": "audio", "kind": "audio_splice", "t": round(truth, 3)})
    for i in range(n_per // 2):
        low_sr = int(rng.choice([8000, 11025, 16000]))
        y = synth.band_limited(synth.recording(6.0, 700 + i, low_sr), low_sr, 44100)
        p = d / f"upsampled_{i}.wav"
        synth.write_wav(p, y, 44100)
        items.append({"path": str(p), "modality": "audio", "kind": "upsampled"})
    for i in range(n_per // 2):   # wide-band clean negatives (44.1 kHz with full-band room noise)
        y = synth.recording(6.0, 800 + i, 44100, float(rng.uniform(-58, -46)), 0.3)
        p = d / f"wideband_{i}.wav"
        synth.write_wav(p, y, 44100)
        items.append({"path": str(p), "modality": "audio", "kind": "clean", "neg_type": "Clean 44.1 kHz recording"})
    items += build_tts(n_per // 2)
    return items


SENTENCES = [
    "The government has decided to declare a three day holiday from tomorrow.",
    "All schools and offices will remain closed during this period.",
    "We request everyone to stay safe and follow only official channels.",
    "The bridge will reopen to traffic on Monday morning after repairs.",
    "Heavy rain is expected across the coastal districts this weekend.",
    "The new metro line will start running from the first of next month.",
    "Our teams are on the ground and relief camps are now open.",
    "Fuel prices will not change for the next two weeks.",
    "The exam results will be published online on Friday evening.",
    "Water supply will be cut in the eastern wards for twelve hours.",
]


def build_tts(n: int) -> list[dict]:
    """Real synthetic speech from macOS `say` (offline). Piper is not installed; see decisions D-14."""
    if shutil.which("say") is None:
        return []
    d = DATA / "tts"
    d.mkdir(parents=True, exist_ok=True)
    items = []
    for i in range(min(n, len(SENTENCES))):
        aiff, wav = d / f"tts_{i}.aiff", d / f"tts_{i}.wav"
        if not wav.exists():
            subprocess.run(["say", "-v", ["Samantha", "Daniel", "Aman", "Karen", "Rishi"][i % 5], "-o", str(aiff), SENTENCES[i]],
                           check=False, capture_output=True)
            if not aiff.exists():
                subprocess.run(["say", "-o", str(aiff), SENTENCES[i]], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff), "-ar", "44100", "-ac", "1", str(wav)], check=True)
            aiff.unlink(missing_ok=True)
        items.append({"path": str(wav), "modality": "audio", "kind": "tts", "sentence": SENTENCES[i]})
    return items


def build_video(n_per: int, rng: np.random.Generator) -> list[dict]:
    d = DATA / "video"
    d.mkdir(parents=True, exist_ok=True)
    photos = synth.photos()
    items = []
    fps = 25
    for i in range(n_per * 3):
        name, rgb = photos[i % len(photos)]
        frames = synth.pan_frames(synth.crops(rgb, 384, 1, rng)[0], 6.0, fps, (320, 240), seed=900 + i)
        kind, truth = ("clean", None)
        if i % 3 == 1:
            at = int(rng.integers(40, 110))
            frames = synth.jump_edit(frames, at, int(rng.integers(8, 20)))
            kind, truth = "video_jump", at / fps
        elif i % 3 == 2:
            at = int(rng.integers(40, 110))
            frames = synth.duplicate_edit(frames, at, 1)
            kind, truth = "video_duplicate", at / fps
        p = d / f"{kind}_{i}.mp4"
        if not p.exists():
            synth.write_video(p, frames, fps)
        items.append({"path": str(p), "modality": "video", "kind": kind, "t": truth,
                      "neg_type": "Clean camera pan" if kind == "clean" else None})
    return items


def build_text(img_items: list[dict], tts_items: list[dict]) -> list[dict]:
    """Caption cases: date conflict vs consistent date (against image EXIF); quoted speech vs TTS transcript."""
    d = DATA / "text"
    d.mkdir(parents=True, exist_ok=True)
    items = []
    edited = [x for x in img_items if x["kind"] == "exif_edit"]
    cams = [x for x in img_items if x["neg_type"] == "Camera JPEG with EXIF"]
    for i, img in enumerate(edited):
        p = d / f"date_conflict_{i}.txt"
        p.write_text(f"Photo from the rally, taken live today — 12 Nov 2026. Share widely.", "utf-8")
        items.append({"path": str(p), "modality": "text", "kind": "date_conflict", "with_image": img["path"]})
    for i, img in enumerate(cams[: len(edited)]):
        p = d / f"date_ok_{i}.txt"
        p.write_text("Photo from the rally on 12 Nov 2026. Share widely.", "utf-8")
        items.append({"path": str(p), "modality": "text", "kind": "clean", "with_image": img["path"],
                      "neg_type": "Caption with matching date"})
    for i, t in enumerate(tts_items):
        good = t["sentence"]
        bad = SENTENCES[(i + 3) % len(SENTENCES)]
        for kind, quote in (("clean", good), ("speech_mismatch", bad)):
            p = d / f"quote_{kind}_{i}.txt"
            p.write_text(f'The official said: "{quote}"', "utf-8")
            items.append({"path": str(p), "modality": "text", "kind": kind, "with_audio": t["path"],
                          "neg_type": "Caption quoting the speech" if kind == "clean" else None})
    return items


# ------------------------------------------------------------------ evaluation

def is_hit(f, item: dict) -> bool:
    kind = item["kind"]
    if f.indicator not in TARGETS or kind not in TARGETS[f.indicator]:
        return False
    loc = f.location
    if item.get("mask") and loc.get("type") == "bbox":
        mask = np.load(item["mask"])
        boxes = [loc] + ([loc["pair"]] if loc.get("pair") else [])
        return max(_iou(b, mask) for b in boxes) >= 0.1
    if item.get("t") is not None and loc.get("start") is not None:
        return abs(float(loc["start"]) - item["t"]) <= 0.5 or float(loc["start"]) <= item["t"] <= float(loc.get("end", loc["start"]))
    return True


def _iou(b: dict, mask: np.ndarray) -> float:
    m = np.zeros_like(mask)
    m[b["y"]:b["y"] + b["h"], b["x"]:b["x"] + b["w"]] = True
    return float((m & mask).sum() / max((m | mask).sum(), 1))


def analyze(item: dict, work: Path, transcripts: dict) -> list:
    p = Path(item["path"])
    if item["modality"] == "image":
        return run_steps(ctx_for(p, "image", work), ["exif", "ela", "noise", "jpeg_ghost", "copy_move"])
    if item["modality"] == "audio":
        ctx = ctx_for(p, "audio", work)
        keys = ["noise_floor", "band_limit", "prosody"] + (["transcript"] if item["kind"] == "tts" else [])
        out = run_steps(ctx, keys)
        if "transcript" in ctx.extra:
            transcripts[item["path"]] = ctx.extra["transcript"]
        return out
    if item["modality"] == "video":
        return run_steps(ctx_for(p, "video", work), ["frames", "frame_dupes", "optical_flow"])
    tctx = ctx_for(p, "text", work, "E-02")
    others = []
    if item.get("with_image"):
        others.append(ctx_for(Path(item["with_image"]), "image", work / "img", "E-01"))
    if item.get("with_audio"):
        tctx.shared = {"transcripts": {"E-01": transcripts[item["with_audio"]]}}
    tctx.case_evidence = others + [tctx]
    return consistency.run(tctx)


def platt(scores: np.ndarray, labels: np.ndarray, rng: np.random.Generator, n_boot: int = 200) -> dict | None:
    from sklearn.linear_model import LogisticRegression

    if len(scores) < 6:
        return None
    if len(set(labels.tolist())) < 2:
        # Every finding of this indicator was right (or every one wrong): calibrate to the hit rate (A = 0).
        # The range comes from the Beta(pos+1, neg+1) posterior, so 16/16 on a small set is not read as certainty.
        pos, neg = int(labels.sum()), int(len(labels) - labels.sum())
        logit = lambda r: float(np.log(r / (1 - r)))  # noqa: E731
        boot = [[0.0, round(logit(min(max(rng.beta(pos + 1, neg + 1), 1e-4), 1 - 1e-4)), 5)] for _ in range(n_boot)]
        return {"A": 0.0, "B": round(logit((pos + 1) / (len(labels) + 2)), 5), "n": int(len(scores)), "positives": pos,
                "boot": boot, "constant": True}

    def fit(x, y):
        if len(set(y.tolist())) < 2:
            return None
        m = LogisticRegression(C=10.0).fit(x.reshape(-1, 1), y)
        return float(m.coef_[0][0]), float(m.intercept_[0])

    A, B = fit(scores, labels)
    boot = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(scores), len(scores))
        r = fit(scores[idx], labels[idx])
        if r:
            boot.append([round(r[0], 5), round(r[1], 5)])
    return {"A": round(A, 5), "B": round(B, 5), "n": int(len(scores)), "positives": int(labels.sum()), "boot": boot}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smaller set for a fast check")
    args = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    n = 8 if args.quick else 24
    print(f"Building seeded test set (seed {SEED}, {'quick' if args.quick else 'full'})…")
    if DATA.exists():
        shutil.rmtree(DATA)
    images = build_images(n, rng)
    audio = build_audio(n // 2 + 4, rng)
    video = build_video(max(3, n // 3), rng)
    tts = [a for a in audio if a["kind"] == "tts"]
    print(f"  {len(images)} images · {len(audio)} audio ({len(tts)} TTS) · {len(video)} videos")

    transcripts: dict = {}
    results = []
    work_root = Path(tempfile.mkdtemp(prefix="tl-val-"))
    all_items = images + audio + video
    for i, item in enumerate(all_items):
        results.append((item, analyze(item, work_root / f"w{i}", transcripts)))
    text = build_text(images, tts)
    for i, item in enumerate(text):
        results.append((item, analyze(item, work_root / f"t{i}", transcripts)))
    print(f"  analyzed {len(results)} items in {time.time() - t0:.0f} s")

    per: dict[str, dict] = defaultdict(lambda: {"scores": [], "labels": [], "tp_items": set(), "fp_items": set()})
    ious, a_err, v_err = [], [], []
    for idx, (item, findings) in enumerate(results):
        for f in findings:
            if f.indicator not in INDICATOR_INFO:
                continue
            hit = is_hit(f, item)
            rec = per[f.indicator]
            rec["scores"].append(f.raw_score)
            rec["labels"].append(1 if hit else 0)
            if hit:
                rec["tp_items"].add(idx)
            if item["kind"] == "clean":
                rec["fp_items"].add(idx)
        # localisation quality on detected tampered items
        if item.get("mask"):
            boxes = [b for f in findings if f.location.get("type") == "bbox" and f.indicator in INDICATOR_INFO
                     for b in [f.location] + ([f.location["pair"]] if f.location.get("pair") else [])]
            if boxes:
                ious.append(max(_iou(b, np.load(item["mask"])) for b in boxes))
        if item["kind"] == "audio_splice":
            ts = [float(f.location["start"]) for f in findings if f.indicator == "noise_floor_step"]
            if ts:
                a_err.append(min(abs(t - item["t"]) for t in ts))
        if item["kind"] in ("video_jump", "video_duplicate"):
            ts = [float(f.location["start"]) for f in findings if f.indicator in ("flow_discontinuity", "duplicate_frames")]
            if ts:
                v_err.append(min(abs(t - item["t"]) for t in ts))

    def count(pred) -> int:
        return sum(1 for item, _ in results if pred(item))

    indicators, calibration = [], {}
    cal_rng = np.random.default_rng(SEED)
    for key, (name, modality, icon) in INDICATOR_INFO.items():
        rec = per.get(key, {"scores": [], "labels": [], "tp_items": set(), "fp_items": set()})
        targets = [i for i, (item, _) in enumerate(results) if item["kind"] in TARGETS[key]]
        negatives = [i for i, (item, _) in enumerate(results) if item["kind"] == "clean" and item["modality"] == modality]
        detected = len(set(targets) & rec["tp_items"])
        fp = len(set(negatives) & rec["fp_items"])
        n_find = len(rec["labels"])
        precision = sum(rec["labels"]) / n_find if n_find else None
        indicators.append({"key": key, "name": name, "modality": modality, "icon": icon,
                           "n_targets": len(targets), "detected": detected,
                           "recall": round(detected / len(targets), 3) if targets else None,
                           "n_negatives": len(negatives), "false_positives": fp,
                           "fpr": round(fp / len(negatives), 3) if negatives else None,
                           "n_findings": n_find, "precision": None if precision is None else round(precision, 3)})
        fit = platt(np.array(rec["scores"]), np.array(rec["labels"]), cal_rng)
        if fit:
            calibration[key] = fit
        indicators[-1]["calibrated"] = bool(fit)

    # reliability: 5-fold cross-validated calibrated probability vs observed hit rate, all indicators pooled
    from sklearn.linear_model import LogisticRegression

    preds, obs = [], []
    for key, rec in per.items():
        x, y = np.array(rec["scores"]), np.array(rec["labels"])
        if len(x) < 10 or len(set(y.tolist())) < 2:
            continue
        folds = np.arange(len(x)) % 5
        np.random.default_rng(SEED).shuffle(folds)
        for k in range(5):
            tr, te = folds != k, folds == k
            if te.sum() == 0 or len(set(y[tr].tolist())) < 2:
                continue
            m = LogisticRegression(C=10.0).fit(x[tr].reshape(-1, 1), y[tr])
            preds += m.predict_proba(x[te].reshape(-1, 1))[:, 1].tolist()
            obs += y[te].tolist()
    reliability = []
    preds_a, obs_a = np.array(preds), np.array(obs)
    for lo in np.arange(0, 1.0, 0.1):
        sel = (preds_a >= lo) & (preds_a < lo + 0.1 + (1e-9 if lo >= 0.9 else 0))
        reliability.append({"bin_lo": round(float(lo), 1), "bin_hi": round(float(lo + 0.1), 1), "mid": round(float(lo + 0.05), 2),
                            "count": int(sel.sum()), "observed": round(float(obs_a[sel].mean()), 3) if sel.any() else None,
                            "predicted": round(float(preds_a[sel].mean()), 3) if sel.any() else None})

    fps = []
    neg_types = sorted({item["neg_type"] for item, _ in results if item.get("neg_type")})
    for nt in neg_types:
        idxs = [i for i, (item, _) in enumerate(results) if item.get("neg_type") == nt]
        hits: dict[str, int] = defaultdict(int)
        for i in idxs:
            for ind in {f.indicator for f in results[i][1] if f.indicator in INDICATOR_INFO}:
                hits[ind] += 1
        for ind, c in sorted(hits.items(), key=lambda kv: -kv[1]):
            fps.append({"type": nt, "indicator": INDICATOR_INFO[ind][0], "fp": c, "n": len(idxs),
                        "label": f"{c}/{len(idxs)}", "cause": FP_CAUSE.get(ind, "")})

    metrics = {
        "version": VERSION, "seed": SEED, "quick": args.quick,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "label": "Small self-made test set. Not a general accuracy claim.",
        "n_items": len(results),
        "sets": {m: {"total": count(lambda it, m=m: it["modality"] == m),
                     "untouched": count(lambda it, m=m: it["modality"] == m and it["kind"] == "clean")}
                 for m in ("image", "audio", "video", "text")},
        "sources": "Crops of the public-domain sample photos bundled with scikit-image; synthetic voiced speech with room "
                   "noise; macOS `say` text-to-speech; camera pans rendered from the sample photos.",
        "indicators": indicators,
        "localization": {"image_iou_mean": round(float(np.mean(ious)), 3) if ious else None, "image_n": len(ious),
                         "audio_splice_err_median_s": round(float(np.median(a_err)), 3) if a_err else None,
                         "audio_n": len(a_err),
                         "video_edit_err_median_s": round(float(np.median(v_err)), 3) if v_err else None, "video_n": len(v_err)},
        "reliability": reliability, "false_positives": fps,
        "not_validated": ["face_flicker", "lipsync_weak", "frame_ela_inconsistency", "frame_noise_inconsistency",
                          "claim_place_conflict", "claim_number_conflict", "modified_after_capture", "camera_tags_missing"],
        "runtime_s": round(time.time() - t0, 1),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (RESULTS / "calibration.json").write_text(json.dumps({"version": f"{VERSION} seed {SEED}", "indicators": calibration}, indent=2))
    shutil.rmtree(work_root, ignore_errors=True)
    print(f"\nWrote {RESULTS / 'metrics.json'} and calibration.json in {metrics['runtime_s']} s\n")
    print(f"{'indicator':24s} {'recall':>7s} {'FPR':>7s} {'prec':>6s}  n_find  calibrated")
    for r in indicators:
        f = lambda v: "   —" if v is None else f"{v:6.2f}"  # noqa: E731
        print(f"{r['key']:24s} {f(r['recall']):>7s} {f(r['fpr']):>7s} {f(r['precision']):>6s}  {r['n_findings']:6d}  {r['calibrated']}")
    print("localisation:", metrics["localization"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

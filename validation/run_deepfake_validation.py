"""Measure and calibrate the learned deepfake detectors on labelled real-vs-AI samples.

    python validation/fetch_deepfake_sets.py      # once: download the samples
    python validation/run_deepfake_validation.py

Writes validation/results/deepfake_calibration.json (Platt parameters + bootstrap, read by the scorer) and adds a
"deepfake" section to validation/results/metrics.json (AUC, accuracy, detection and false-alarm rates, reliability,
all from 5-fold cross-validation). Video frames use the image detectors, so "ai_video" reuses the image calibration
and is marked as not separately validated.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.analyzers import deepfake as det  # noqa: E402

DATA = ROOT / "validation" / "data" / "deepfake"
RESULTS = ROOT / "validation" / "results"
SEED = 7


def auc(y: np.ndarray, s: np.ndarray) -> float:
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    wins = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(wins / (len(pos) * len(neg)))


def platt_fit(x: np.ndarray, y: np.ndarray):
    from sklearn.linear_model import LogisticRegression

    m = LogisticRegression(C=10.0).fit(x.reshape(-1, 1), y)
    return float(m.coef_[0][0]), float(m.intercept_[0])


def sig(z):
    return 1 / (1 + np.exp(-z))


def evaluate(name: str, scores: list[float], labels: list[int], extra: dict | None = None) -> tuple[dict, dict]:
    x, y = np.array(scores, float), np.array(labels, int)
    rng = np.random.default_rng(SEED)
    folds = rng.permutation(np.arange(len(x)) % 5)
    cv = np.zeros(len(x))
    for k in range(5):
        tr, te = folds != k, folds == k
        a, b = platt_fit(x[tr], y[tr])
        cv[te] = sig(a * x[te] + b)
    A, B = platt_fit(x, y)
    boot = []
    for _ in range(200):
        idx = rng.integers(0, len(x), len(x))
        if len(set(y[idx])) == 2:
            a, b = platt_fit(x[idx], y[idx])
            boot.append([round(a, 5), round(b, 5)])
    pred = cv >= 0.5
    tp, fp = int((pred & (y == 1)).sum()), int((pred & (y == 0)).sum())
    tn, fn = int((~pred & (y == 0)).sum()), int((~pred & (y == 1)).sum())
    rel = []
    for lo in np.arange(0, 1, 0.1):
        sel = (cv >= lo) & (cv < lo + 0.1 + (1e-9 if lo >= 0.9 else 0))
        rel.append({"bin_lo": round(float(lo), 1), "mid": round(float(lo + 0.05), 2), "count": int(sel.sum()),
                    "predicted": round(float(cv[sel].mean()), 3) if sel.any() else None,
                    "observed": round(float(y[sel].mean()), 3) if sel.any() else None})
    metrics = {"detector": name, "n": int(len(x)), "n_ai": int(y.sum()), "n_real": int((y == 0).sum()),
               "auc": round(auc(y, x), 3), "accuracy": round((tp + tn) / len(x), 3),
               "detection_rate": round(tp / max(tp + fn, 1), 3), "false_alarm_rate": round(fp / max(fp + tn, 1), 3),
               "raw_accuracy_at_0_5": round(float(((x >= 0.5) == y).mean()), 3), "reliability": rel} | (extra or {})
    cal = {"A": round(A, 5), "B": round(B, 5), "n": int(len(x)), "auc": metrics["auc"], "boot": boot}
    print(f"  {name:10s} n={len(x):3d}  AUC {metrics['auc']:.3f}  acc {metrics['accuracy']:.3f}  "
          f"detect {metrics['detection_rate']:.3f}  false alarm {metrics['false_alarm_rate']:.3f}")
    return metrics, cal


def pick(name: str, candidates: dict[str, list[float]], y: list[int], extra: dict) -> tuple[dict, dict]:
    """Measure every candidate model and keep the best by AUC; within 0.01 of the best, the earlier candidate in the
    analyzer's list wins (the lists put models with documented training data first)."""
    yy = np.array(y)
    aucs = {m: round(auc(yy, np.array(v)), 3) for m, v in candidates.items()}
    top = max(aucs.values())
    best = next(m for m in candidates if aucs[m] >= top - 0.01)
    print(f"  {name} candidates AUC: {aucs} -> {best}")
    metrics, cal = evaluate(name, candidates[best], y, {"model": best, "candidates_auc": aucs} | extra)
    return metrics, cal | {"models": [best]}


def main() -> int:
    manifest = json.loads((DATA / "manifest.json").read_text())
    t0 = time.time()
    out_metrics, out_cal = [], {}

    imgs = [m for m in manifest if m["modality"] == "image"]
    if imgs:
        from PIL import Image

        pics = [Image.open(DATA / m["path"]).convert("RGB") for m in imgs]
        y = [1 if m["label"] == "fake" else 0 for m in imgs]
        cands = {}
        for name in det.IMAGE_MODELS:
            if det.available(name):
                t = time.time()
                cands[name] = det.image_scores(pics, models=[name])[name]
                print(f"  scored {len(pics)} images with {name} in {time.time() - t:.0f} s")
        gens = sorted({m.get("generator") or "?" for m in imgs if m["label"] == "fake"})
        m_img, c_img = pick("ai_image", cands, y, {"generators": gens,
                                                    "source": "ComplexDataLab/OpenFake core/test (CC BY-NC 4.0)"})
        out_metrics.append(m_img)
        out_cal["ai_image"] = c_img
        out_cal["ai_video"] = {**c_img, "note": "video frames use the image detector; calibration reused, not separately validated"}

    auds = [m for m in manifest if m["modality"] == "audio"]
    if auds:
        import soundfile as sf

        y = [1 if m["label"] == "fake" else 0 for m in auds]
        cands = {}
        for name in det.AUDIO_MODELS:
            if not det.available(name):
                continue
            scores = []
            for m in auds:
                yv, sr = sf.read(DATA / m["path"], dtype="float32")
                if yv.ndim > 1:
                    yv = yv.mean(axis=1)
                scores.append(float(np.median(det.voice_scores(yv, sr, name=name))))
            cands[name] = scores
        m_aud, c_aud = pick("ai_voice", cands, y, {"source": "SpeechAntiSpoofingBenchmarks/InTheWild (Apache 2.0)"})
        out_metrics.append(m_aud)
        out_cal["ai_voice"] = c_aud

    txts = [m for m in manifest if m["modality"] == "text"]
    if txts:
        texts = [(DATA / m["path"]).read_text("utf-8") for m in txts]
        y = [1 if m["label"] == "fake" else 0 for m in txts]
        cands = {n: det.text_scores(texts, name=n) for n in det.TEXT_MODELS if det.available(n)}
        m_txt, c_txt = pick("ai_text", cands, y, {"source": "textsightai/ai-text-detection-benchmark-2026 (CC BY-SA 4.0)"})
        short = det.text_scores([" ".join(t.split()[:30]) for t in texts], name=m_txt["model"])
        m_txt["short_text_auc_30_words"] = round(auc(np.array(y), np.array(short)), 3)
        print(f"  ai_text on the first 30 words only: AUC {m_txt['short_text_auc_30_words']}")
        out_metrics.append(m_txt)
        out_cal["ai_text"] = c_txt

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "deepfake_calibration.json").write_text(json.dumps({"version": "deepfake v1 seed 7", "detectors": out_cal}, indent=1))
    mp = RESULTS / "metrics.json"
    metrics = json.loads(mp.read_text()) if mp.exists() else {}
    metrics["deepfake"] = {"detectors": out_metrics, "runtime_s": round(time.time() - t0, 1),
                           "label": "Small public labelled samples. The best model per modality was chosen on these same "
                                    "samples, and accuracy on other generators and on compressed social-media copies "
                                    "will be lower."}
    mp.write_text(json.dumps(metrics, indent=2))
    print(f"wrote deepfake_calibration.json and metrics.json[deepfake] in {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Face-region flicker (§3.4): track the face with MediaPipe and watch its sharpness and colour.

Face-swap and lip-sync edits change the face while the background stays steady. The same pass
records mouth opening per frame, which the lip-sync rule (R-07) compares with speech energy.
"""
from __future__ import annotations

import cv2
import numpy as np

from ... import config
from ..base import AnalysisContext, RawFinding, fmt_t, robust_z, squash
from .frames import decode

SAMPLE_FPS = 8.0
WORK_W = 640


MODEL = "face_landmarker.task"


def _landmarker():
    """MediaPipe Tasks face landmarker (IMAGE mode, so results do not depend on tracking state)."""
    from mediapipe.tasks.python import BaseOptions, vision

    path = config.MODEL_DIR / MODEL
    if not path.exists():
        raise RuntimeError(f"{MODEL} not found in {config.MODEL_DIR} (run make setup)")
    opts = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(path)),
                                        running_mode=vision.RunningMode.IMAGE, num_faces=1,
                                        min_face_detection_confidence=0.5)
    return vision.FaceLandmarker.create_from_options(opts)


def track(ctx: AnalysisContext) -> dict:
    fr = decode(ctx)
    t_all = fr["t"]
    step = max(1, int(round(fr["fps"] / SAMPLE_FPS)))
    cap = cv2.VideoCapture(str(ctx.original))
    rows = []
    import mediapipe as mp

    mesh = _landmarker()
    try:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok or idx >= len(t_all):
                break
            if idx % step == 0:
                h, w = frame.shape[:2]
                frame = cv2.resize(frame, (WORK_W, int(h * WORK_W / w)), interpolation=cv2.INTER_AREA)
                h, w = frame.shape[:2]
                res = mesh.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
                if res.face_landmarks:
                    lm = res.face_landmarks[0]
                    xs, ys = np.array([p.x for p in lm]) * w, np.array([p.y for p in lm]) * h
                    x0, x1, y0, y1 = int(max(0, xs.min())), int(min(w, xs.max())), int(max(0, ys.min())), int(min(h, ys.max()))
                    if x1 - x0 > 20 and y1 - y0 > 20:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        lap = cv2.Laplacian(gray, cv2.CV_32F)
                        face = np.zeros_like(gray, bool)
                        face[y0:y1, x0:x1] = True
                        lab = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2LAB)
                        rows.append({"i": idx, "t": float(t_all[idx]), "box": [x0 / w, y0 / h, (x1 - x0) / w, (y1 - y0) / h],
                                     "face_sharp": float(lap[face].var()), "bg_sharp": float(lap[~face].var()),
                                     "face_L": float(lab[..., 0].mean()),
                                     "mouth": float(abs(lm[14].y - lm[13].y) * h / max(y1 - y0, 1))})
            idx += 1
    finally:
        mesh.close()
        cap.release()
    return {"rows": rows, "step": step}


def run(ctx: AnalysisContext) -> list[RawFinding]:
    tr = track(ctx)
    rows = tr["rows"]
    ctx.shared.setdefault("mouth", {})[ctx.label] = [(r["t"], r["mouth"]) for r in rows]
    ctx.extra["face"] = {"frames_with_face": len(rows), "boxes": [[r["t"], *[round(v, 4) for v in r["box"]]] for r in rows]}
    if len(rows) < 8:
        ctx.log("video", f"face region: face found in {len(rows)} sampled frames, too few to measure flicker")
        return []
    t = np.array([r["t"] for r in rows])
    ratio = np.log((np.array([r["face_sharp"] for r in rows]) + 1) / (np.array([r["bg_sharp"] for r in rows]) + 1))
    bg = np.log(np.array([r["bg_sharp"] for r in rows]) + 1)
    lum = np.array([r["face_L"] for r in rows])
    zr, zb, zl = robust_z(ratio), robust_z(bg), robust_z(lum)
    score = np.maximum(np.abs(zr), np.abs(zl) * 0.7)
    mask = (score > config.FACE_FLICKER_Z) & (np.abs(zb) < 2.5)
    ctx.extra["_face_z"] = (t, score)
    findings = []
    i = 0
    while i < len(mask):
        if not mask[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(mask) and (mask[j + 1] or (j + 2 < len(mask) and mask[j + 2])):
            j += 1
        seg = slice(i, j + 1)
        peak = float(score[seg].max())
        box = rows[i]["box"]
        W, H = ctx.metadata.get("width") or 1, ctx.metadata.get("height") or 1
        findings.append(RawFinding(
            indicator="face_flicker", family="face_flicker", name="Face-region flicker",
            location={"type": "frame_range", "start": float(t[i]), "end": float(t[j]) + 1 / SAMPLE_FPS,
                      "frames": [rows[i]["i"], rows[j]["i"]], "x": int(box[0] * W), "y": int(box[1] * H),
                      "w": int(box[2] * W), "h": int(box[3] * H), "image_w": W, "image_h": H},
            loc_label=f"{fmt_t(t[i])}–{fmt_t(t[j])} · face region",
            raw_score=squash(peak, mid=config.FACE_FLICKER_Z + 2.5, scale=1.2),
            method=f"MediaPipe face mesh at {SAMPLE_FPS:g} fps; face/background sharpness ratio and face luminance, robust z "
                   f"peak {peak:.1f} (threshold {config.FACE_FLICKER_Z:g}) while background |z| < 2.5",
            explanation=f"Between {fmt_t(t[i])} and {fmt_t(t[j])} the face region changes sharpness or brightness while the "
                        f"background stays steady. Face replacement and lip-sync edits often show this.",
            alternatives=["Autofocus hunting on the face", "Lighting change that falls only on the speaker",
                          "The speaker turning or leaning towards the camera"],
            sort=float(t[i]), extra={"peak_z": round(peak, 2)}))
        i = j + 1
    ctx.log("video", f"face region: tracked in {len(rows)} sampled frames, {len(findings)} flicker segment(s)")
    return findings

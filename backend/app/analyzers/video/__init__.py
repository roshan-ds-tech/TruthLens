"""Video analyzer (§3.4) plus container metadata rules shared by video and audio."""
from __future__ import annotations

import numpy as np

from ... import config
from ..base import AnalysisContext, FnAnalyzer, RawFinding, fmt_t, squash
from ..image import ela, noise
from . import face_flicker, flow_jumps, frames, phash_dupes

EDITOR_ENCODERS = ("premiere", "capcut", "inshot", "final cut", "davinci", "kinemaster", "filmora", "imovie",
                   "after effects", "vn video", "powerdirector", "clipchamp")


def av_metadata(ctx: AnalysisContext) -> list[RawFinding]:
    m = ctx.metadata
    notes = []
    enc = " ".join(str(v) for v in (m.get("encoder"), m.get("video_encoder")) if v)
    if enc:
        notes.append(f"Encoder tag: {enc}.")
    if not (m.get("make") or m.get("model")):
        notes.append("No camera make or model in the container; common after re-encoding or download.")
    if m.get("r_frame_rate") and m.get("avg_frame_rate") and m["r_frame_rate"] != m["avg_frame_rate"]:
        notes.append(f"Variable frame rate ({m['avg_frame_rate']} average vs {m['r_frame_rate']} nominal).")
    for w in m.get("warnings", []):
        notes.append(w)
    ctx.extra["metadata_notes"] = notes
    hit = next((e for e in EDITOR_ENCODERS if e in enc.lower()), None)
    if not hit:
        return []
    return [RawFinding(
        indicator="editor_encoder_tag", family="metadata", name="Editing software tag",
        location={"type": "file", "field": "encoder"}, loc_label=f"Container encoder · {enc}", raw_score=0.5,
        method="Container encoder tags (ffprobe) compared with a list of video editors",
        explanation=f"The file was last written by video-editing software ({enc}), not directly by a camera.",
        alternatives=["Trimmed, captioned or compressed for sharing without changing content"], sort=0.0)]


def frame_forensics(ctx: AnalysisContext) -> list[RawFinding]:
    """Image pipeline on the most suspicious frames only (RAM and time budget)."""
    fr = frames.decode(ctx)
    t = fr["t"]
    score = np.array(fr.get("flow_z", np.zeros(len(t))), dtype=float)
    if "_face_z" in ctx.extra:
        ft, fz = ctx.extra["_face_z"]
        for tt, zz in zip(ft, fz):
            k = int(np.argmin(np.abs(t - tt)))
            score[k] = max(score[k], zz)
    picks: list[int] = []
    for i in np.argsort(-score, kind="stable"):
        if len(picks) >= config.TOP_SUSPICIOUS_FRAMES:
            break
        if all(abs(t[i] - t[j]) > 1.0 for j in picks):
            picks.append(int(i))
    findings: list[RawFinding] = []
    for i in sorted(picks):
        rgb = frames.read_frame(ctx, i)
        if rgb is None:
            continue
        loc = {"type": "frame_range", "start": float(t[i]), "end": float(t[i]), "frames": [i, i]}
        for f in ela.analyze_array(rgb, ctx, prefix=f"frame{i}_", is_jpeg=False, sort_offset=float(t[i]) * 1e4, extra_loc=loc) + \
                noise.analyze_array(rgb, ctx, prefix=f"frame{i}_", sort_offset=float(t[i]) * 1e4, extra_loc=loc):
            f.indicator = "frame_" + f.indicator
            f.family = "frame_forensics"
            f.name = f"{f.name} (frame {i})"
            f.loc_label = f"{fmt_t(t[i])} · frame {i} · {f.loc_label.lower()}"
            f.raw_score *= 0.8   # video frames are re-encoded H.264, which weakens still-image signals
            f.extra["frame"] = i
            findings.append(f)
    ctx.extra["inspected_frames"] = [{"frame": i, "t": float(t[i])} for i in sorted(picks)]
    ctx.log("video", f"image pipeline on frames {', '.join(str(i) for i in sorted(picks))}: {len(findings)} finding(s)")
    return findings


def suspicion_curve(ctx: AnalysisContext, findings: list[RawFinding]) -> list[float]:
    """Per-second suspicion in [0, 1] for the timeline: flow and face z-scores plus flagged findings."""
    fr = ctx.extra.get("_frames")
    if not fr:
        return []
    t = fr["t"]
    duration = float(t[-1]) if len(t) else 0.0
    n = int(np.ceil(duration)) + 1
    curve = np.full(n, 0.05)
    flow_z = np.asarray(fr.get("flow_z", np.zeros(len(t))))
    for tt, z in zip(t, flow_z):
        curve[int(tt)] = max(curve[int(tt)], squash(z, mid=config.FLOW_Z + 1, scale=1.5) * 0.9)
    if "_face_z" in ctx.extra:
        for tt, z in zip(*ctx.extra["_face_z"]):
            curve[min(int(tt), n - 1)] = max(curve[min(int(tt), n - 1)], squash(z, mid=config.FACE_FLICKER_Z + 1, scale=1.2) * 0.8)
    for f in findings:
        s, e = f.location.get("start"), f.location.get("end")
        if s is None:
            continue
        for sec in range(int(s), min(n, int(np.floor(e)) + 1)):
            curve[sec] = max(curve[sec], f.raw_score)
    return [round(float(v), 3) for v in curve]


def _decode(ctx):  # registered as its own step so progress shows decoding separately
    return frames.run(ctx)


ANALYZERS = [
    FnAnalyzer("av_metadata", "Metadata", ("video", "audio"), av_metadata, "Container metadata",
               "Encoder tags, frame-rate and creation-time checks", "ffprobe rules 1.0"),
    FnAnalyzer("frames", "Keyframes", ("video",), _decode, "Frame sampling", "Decode and downscale frames", "opencv"),
    FnAnalyzer("frame_dupes", "Duplicate frames", ("video",), phash_dupes.run, "Duplicate and dropped frames",
               "pHash duplicates and timestamp gaps", "phash 1.0"),
    FnAnalyzer("optical_flow", "Optical flow", ("video",), flow_jumps.run, "Optical flow",
               "Motion breaks between frames", "farneback 1.0"),
    FnAnalyzer("face_flicker", "Face region", ("video",), face_flicker.run, "Face-region flicker",
               "Face sharpness and colour vs background (MediaPipe)", "mediapipe face mesh", optional_dep="mediapipe"),
    FnAnalyzer("frame_forensics", "Frame forensics", ("video",), frame_forensics, "Frame forensics",
               "Error level and noise map on the most suspicious frames", "image pipeline 1.0"),
]

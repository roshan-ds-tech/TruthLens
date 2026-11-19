"""Named, readable cross-modal rules (§3.7). Each rule is one small function a judge can read.

A rule receives the case's scored findings and evidence and returns edges:
``supports`` (two signals agree) or ``weakens`` (an alternative explanation applies).
Findings from the same method family never corroborate each other (independence rule).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .. import config


@dataclass
class F:
    """A scored finding as the rules see it."""
    finding_id: str
    evidence: str            # "E-01"
    kind: str                # evidence kind
    parent: Optional[str]    # label of the video an audio track came from
    modality: str
    indicator: str
    family: str
    location: dict
    p: float
    extra: dict


@dataclass
class Ev:
    label: str
    kind: str
    parent: Optional[str]
    metadata: dict
    extra: dict


@dataclass
class Edge:
    rule_id: str
    rule_name: str
    source: str              # finding id, evidence label or "PRF"
    target: str
    relation: str            # supports | weakens
    note: str
    weak: bool = False
    weight_scale: dict[str, float] = field(default_factory=dict)   # finding_id → multiplier
    alternative: Optional[tuple[str, str]] = None                  # (finding_id, alternative text)


def _span(f: F) -> tuple[float, float] | None:
    s, e = f.location.get("start"), f.location.get("end")
    return (float(s), float(e if e is not None else s)) if s is not None and f.location["type"] in ("frame_range", "time_range") else None


def _same_timeline(a: F, b: F) -> bool:
    return a.evidence == b.evidence or a.parent == b.evidence or b.parent == a.evidence or (a.parent and a.parent == b.parent) \
        or a.extra.get("video") in (b.evidence,) or a.extra.get("audio") in (b.evidence,)


def r03_splice_sync(fs: list[F], evs: dict[str, Ev]) -> list[Edge]:
    """Audio splice within 0.5 s of a motion break in the same clip → the two support each other."""
    out = []
    audio = [f for f in fs if f.indicator == "noise_floor_step"]
    video = [f for f in fs if f.indicator in ("flow_discontinuity", "duplicate_frames", "dropped_frames")]
    for a in audio:
        for v in video:
            sa, sv = _span(a), _span(v)
            if not (sa and sv and _same_timeline(a, v)):
                continue
            delta = abs(sa[0] - sv[0])
            if delta <= config.SPLICE_SYNC_WINDOW_S or (sv[0] <= sa[0] <= sv[1]):
                out.append(Edge("R-03", "Audio splice within 0.5 s of a motion break", a.finding_id, v.finding_id, "supports",
                                f"{a.finding_id} ↔ {v.finding_id} · Δ {delta:.1f} s"))
    return out


def r05_speech_vs_caption(fs: list[F], evs: dict[str, Ev]) -> list[Edge]:
    """Caption quotes words the transcript does not contain → conflict between text and speech."""
    out = []
    for t in fs:
        if t.indicator != "claim_speech_mismatch":
            continue
        target = t.extra.get("target_evidence")
        window = t.extra.get("time")
        audio_f = [f for f in fs if f.evidence == target and _span(f) and window
                   and _span(f)[0] <= window[1] and _span(f)[1] >= window[0]]
        dest = audio_f[0].finding_id if audio_f else target
        out.append(Edge("R-05", "Caption quote not found in the speech", t.finding_id, dest, "supports",
                        f"{t.finding_id} ↔ {dest} transcript · similarity {t.extra.get('similarity', 0):.2f}"))
    return out


def r07_lipsync(fs: list[F], evs: dict[str, Ev]) -> list[Edge]:
    """Lip-sync drop overlapping a flagged audio or video segment → weak support."""
    out = []
    for x in (f for f in fs if f.indicator == "lipsync_weak"):
        sx = _span(x)
        hits = [f for f in fs if f is not x and f.modality in ("video", "audio") and _span(f) and _same_timeline(x, f)
                and _span(f)[0] <= sx[1] and _span(f)[1] >= sx[0] and f.family not in ("prosody", "band_limit")]
        for h in hits:
            out.append(Edge("R-07", "Lip-sync drop overlaps a flagged segment", x.finding_id, h.finding_id, "supports",
                            f"{x.finding_id} ↔ {h.finding_id}", weak=True))
    return out


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    ix = max(0.0, min(ax0 + aw, bx0 + bw) - max(ax0, bx0))
    iy = max(0.0, min(ay0 + ah, by0 + bh) - max(ay0, by0))
    inter = ix * iy
    return inter / (aw * ah + bw * bh - inter) if inter > 0 else 0.0


def r09_same_location(fs: list[F], evs: dict[str, Ev]) -> list[Edge]:
    """An image region flagged where the video's flagged face region sits → both point at the same place."""
    out = []
    img = [f for f in fs if f.modality == "image" and f.location.get("type") == "bbox"]
    vid = [f for f in fs if f.indicator in ("face_flicker", "frame_ela_inconsistency", "frame_noise_inconsistency")
           and f.location.get("w")]
    for i in img:
        bi = (i.location["x"] / i.location["image_w"], i.location["y"] / i.location["image_h"],
              i.location["w"] / i.location["image_w"], i.location["h"] / i.location["image_h"])
        for v in vid:
            bv = (v.location["x"] / v.location["image_w"], v.location["y"] / v.location["image_h"],
                  v.location["w"] / v.location["image_w"], v.location["h"] / v.location["image_h"])
            iou = _iou(bi, bv)
            if iou >= 0.3 and i.family != v.family:
                out.append(Edge("R-09", "Image region overlaps the flagged face region in the video", i.finding_id,
                                v.finding_id, "supports", f"{i.finding_id} ↔ {v.finding_id} · IoU {iou:.2f}"))
    return out


def r11_claimed_date(fs: list[F], evs: dict[str, Ev]) -> list[Edge]:
    """Claimed date differs from capture metadata → the text conflict finding points at that evidence."""
    out = []
    for t in (f for f in fs if f.indicator == "claim_date_conflict"):
        target = t.extra.get("target_evidence")
        related = sorted((f for f in fs if f.evidence == target and f.family != t.family), key=lambda f: -f.p)
        dest = related[0].finding_id if related else target
        out.append(Edge("R-11", "Claimed date differs from capture metadata", t.finding_id, dest, "supports",
                        f"{t.finding_id} ↔ {dest} · {t.extra.get('gap_days', '?')} days apart"))
    return out


def r14_recompression(fs: list[F], evs: dict[str, Ev]) -> list[Edge]:
    """Error-level pattern on a platform-recompressed image → weakens ELA / ghost (alternative explanation)."""
    out = []
    for f in fs:
        if f.indicator not in ("ela_inconsistency", "jpeg_ghost"):
            continue
        ev = evs.get(f.evidence)
        if not ev:
            continue
        meta = ev.metadata
        q = meta.get("jpeg_quality")
        stripped = not meta.get("exif")
        large = f.extra.get("area_fraction", 0) > 0.25
        if (stripped and q is not None and q <= 85) or large:
            why = (f"no EXIF and JPEG quality ≈{q}, typical of messaging apps" if stripped and q is not None
                   else "the flagged area covers a large share of the image")
            out.append(Edge("R-14", "Error-level pattern matches platform recompression", "PRF", f.finding_id, "weakens",
                            f"{f.finding_id} ↔ platform profile · {why}", weight_scale={f.finding_id: 0.5},
                            alternative=(f.finding_id, f"Platform recompression ({why})")))
    return out


RULES: list[Callable[[list[F], dict[str, Ev]], list[Edge]]] = [
    r03_splice_sync, r05_speech_vs_caption, r07_lipsync, r09_same_location, r11_claimed_date, r14_recompression,
]

RULE_DETAILS = {
    "R-03": "Two independent analyzers point at the same moment.",
    "R-05": "What the caption says was spoken is not in the transcript.",
    "R-07": "Weak on its own; adds little weight.",
    "R-09": "Image and video signals point at the same area.",
    "R-11": "The caption's date conflicts with when the media was captured.",
    "R-14": "Lowers the weight of the error-level finding in the combined range.",
}


def run(fs: list[F], evs: dict[str, Ev]) -> list[Edge]:
    edges: list[Edge] = []
    for rule in RULES:
        edges.extend(rule(fs, evs))
    seen, out = set(), []
    for e in edges:
        key = (e.rule_id, e.source, e.target)
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def independent_supports(edges: list[Edge], fam: dict[str, str]) -> int:
    """Supports edges linking two different method families (the independence rule)."""
    return sum(1 for e in edges if e.relation == "supports" and not e.weak and e.source in fam and e.target in fam
               and fam[e.source] != fam[e.target])


def describe(edge: Edge) -> dict[str, Any]:
    return {"id": edge.rule_id, "name": edge.rule_name, "links": edge.note, "detail": RULE_DETAILS.get(edge.rule_id, ""),
            "relation": edge.relation, "weak": edge.weak,
            "tag": "Weakens" if edge.relation == "weakens" else ("Supports (weak)" if edge.weak else "Supports")}

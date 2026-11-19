"""Compare each caption claim with the other evidence (§3.6): EXIF date and GPS, video creation time,
and transcript text (all-MiniLM-L6-v2 similarity). Each claim ends up consistent, conflict or unverifiable."""
from __future__ import annotations

import gc
import math
import os
import re
from datetime import date, datetime
from typing import Optional

from ... import config
from ..base import AnalysisContext, RawFinding, squash
from . import gazetteer
from .claims import Claim, extract

NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _d(iso: str) -> date:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).date()


def _pretty(iso: str) -> str:
    return _d(iso).strftime("%d %b %Y")


def similarity_backend() -> str:
    try:
        import sentence_transformers  # noqa: F401

        return "all-MiniLM-L6-v2"
    except ImportError:
        return "tf-idf"


def similarities(query: str, candidates: list[str]) -> list[float]:
    """Cosine similarity of ``query`` to each candidate. MiniLM if installed, TF-IDF otherwise."""
    if not candidates:
        return []
    if similarity_backend() == "all-MiniLM-L6-v2":
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer

        local = config.MODEL_DIR / "all-MiniLM-L6-v2"
        model = SentenceTransformer(str(local) if local.exists() else config.SIMILARITY_MODEL, device="cpu")
        try:
            emb = model.encode([query] + candidates, normalize_embeddings=True, convert_to_numpy=True)
            return [round(float(emb[0] @ e), 4) for e in emb[1:]]
        finally:
            del model
            gc.collect()
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    m = TfidfVectorizer(ngram_range=(1, 2)).fit_transform([query] + candidates)
    return [round(float(v), 4) for v in cosine_similarity(m[0], m[1:])[0]]


def _transcript_windows(tr: dict) -> list[tuple[str, float, float]]:
    segs = tr.get("segments", [])
    wins = [(s["text"], s["start"], s["end"]) for s in segs]
    wins += [(a["text"] + " " + b["text"], a["start"], b["end"]) for a, b in zip(segs, segs[1:])]
    return [w for w in wins if w[0].strip()]


def _dated_sources(ctx: AnalysisContext) -> list[tuple[str, str, str]]:
    """(evidence label, field name, ISO date) for every other item with a capture or creation date."""
    out = []
    for o in ctx.case_evidence:
        if o.label == ctx.label:
            continue
        if o.kind == "image" and o.metadata.get("date_original"):
            out.append((o.label, "EXIF DateTimeOriginal", o.metadata["date_original"]))
        if o.kind == "video" and o.metadata.get("creation_time"):
            out.append((o.label, "Video creation time", o.metadata["creation_time"]))
    return out


def _number_in(text: str, unit: str) -> Optional[int]:
    m = re.search(rf"\b(\d+|{'|'.join(NUM_WORDS)})(?:\s*|-){unit.rstrip('s')}s?\b", text, re.I)
    if not m:
        return None
    tok = m.group(1).lower()
    return int(tok) if tok.isdigit() else NUM_WORDS[tok]


def run(ctx: AnalysisContext) -> list[RawFinding]:
    text = ctx.original.read_text("utf-8")
    claims = extract(text)
    transcripts = ctx.shared.get("transcripts", {})
    findings: list[RawFinding] = []
    sources = _dated_sources(ctx)

    for c in claims:
        if c.kind == "date" and c.value:
            for label, field, iso in sources:
                gap = abs((_d(c.value) - _d(iso)).days)
                c.evidence.append(f"{label} {field}")
                if gap <= 2:
                    c.status, c.detail = "consistent", f"matches {field} of {label}"
                    continue
                c.status, c.detail = "conflict", f"{field} of {label} is {_pretty(iso)} ({gap} days apart)"
                findings.append(RawFinding(
                    indicator="claim_date_conflict", family="claim_date", name="Date conflict",
                    location={"type": "text_span", "start": c.start, "end": c.end},
                    loc_label=f"Caption ↔ {field} of {label}",
                    raw_score=squash(math.log10(gap + 1), mid=1.0, scale=0.35),
                    method=f"dateparser on the caption; compared with {field} of {label}: {gap} days apart (tolerance 2)",
                    explanation=f"The caption dates the event to {_pretty(c.value)}. {field} of {label} says {_pretty(iso)}.",
                    alternatives=["Camera clock set incorrectly",
                                  "The caption gives the posting date, not the capture date",
                                  "Metadata carried over from a template or earlier file"],
                    sort=c.start,
                    extra={"compare": [{"k": "Caption", "v": _pretty(c.value)},
                                       {"k": field, "v": _pretty(iso), "conflict": True}],
                           "target_evidence": label, "gap_days": gap}))
        elif c.kind == "date" and c.relative:
            c.detail = "relative date with no known posting time"

        elif c.kind == "quote" and transcripts:
            best = (0.0, None, None)
            for label, tr in transcripts.items():
                wins = _transcript_windows(tr)
                sims = similarities(c.text, [w[0] for w in wins])
                for s, w in zip(sims, wins):
                    if s > best[0]:
                        best = (s, label, w)
            sim, label, win = best
            c.evidence = [f"{label} transcript"] if label else []
            if label is None or sim < config.SPEECH_MISMATCH_SIM:
                c.status, c.detail = "conflict", f"closest transcript sentence similarity {sim:.2f}"
                target = label or next(iter(transcripts))
                findings.append(RawFinding(
                    indicator="claim_speech_mismatch", family="claim_speech", name="Quoted speech not found in audio",
                    location={"type": "text_span", "start": c.start, "end": c.end},
                    loc_label=f"Caption quote ↔ transcript of {target}",
                    raw_score=squash(config.SPEECH_MISMATCH_SIM - sim, mid=0.12, scale=0.06),
                    method=f"{similarity_backend()} cosine similarity between the quote and every transcript sentence "
                           f"window: best {sim:.2f} (threshold {config.SPEECH_MISMATCH_SIM})",
                    explanation=f"The caption attributes words to the speaker that do not appear in what is said in {target}: "
                                f"the closest sentence has similarity {sim:.2f}.",
                    alternatives=["The caption paraphrases loosely or summarises", "Transcript errors on noisy audio"],
                    sort=c.start,
                    extra={"compare": [{"k": "Caption", "v": c.text[:80]},
                                       {"k": "Closest speech", "v": (win[0][:80] if win else "—"), "conflict": True}],
                           "target_evidence": target, "similarity": sim, "time": [win[1], win[2]] if win else None}))
            else:
                c.status = "consistent" if sim >= 0.6 else "unverifiable"
                c.detail = f"transcript at {win[1]:.1f}–{win[2]:.1f} s, similarity {sim:.2f}"

        elif c.kind == "place":
            pos = gazetteer.lookup(c.text)
            gps = next(((o.label, o.metadata["gps"]) for o in ctx.case_evidence if o.metadata.get("gps")), None)
            if pos and gps:
                dist = gazetteer.km(pos, (gps[1]["lat"], gps[1]["lon"]))
                c.evidence = [f"{gps[0]} EXIF GPS"]
                if dist <= 150:
                    c.status, c.detail = "consistent", f"GPS {dist:.0f} km from {c.text}"
                else:
                    c.status, c.detail = "conflict", f"GPS {dist:.0f} km from {c.text}"
                    findings.append(RawFinding(
                        indicator="claim_place_conflict", family="claim_entity", name="Place conflict",
                        location={"type": "text_span", "start": c.start, "end": c.end},
                        loc_label=f"Caption '{c.text}' ↔ GPS of {gps[0]}",
                        raw_score=squash(math.log10(dist), mid=2.6, scale=0.3),
                        method=f"Gazetteer position of '{c.text}' vs EXIF GPS of {gps[0]}: {dist:.0f} km (tolerance 150 km)",
                        explanation=f"The caption places the scene in {c.text}, but the photo's GPS tag is {dist:.0f} km away.",
                        alternatives=["Photo taken elsewhere and shared as a related image", "GPS tag from a later edit or sync"],
                        sort=c.start, extra={"distance_km": round(dist), "target_evidence": gps[0]}))
            elif pos is None:
                c.detail = "place not in the offline gazetteer"

        elif c.kind == "number" and transcripts:
            unit = c.value.split()[1] if c.value else ""
            claimed = int(float(c.value.split()[0].replace(",", ""))) if c.value else None
            for label, tr in transcripts.items():
                said = _number_in(" ".join(s["text"] for s in tr.get("segments", [])), unit)
                if said is None:
                    continue
                c.evidence = [f"{label} transcript"]
                if said == claimed:
                    c.status, c.detail = "consistent", f"transcript also says {said} {unit}"
                else:
                    c.status, c.detail = "conflict", f"transcript says {said} {unit}"
                    findings.append(RawFinding(
                        indicator="claim_number_conflict", family="claim_entity", name="Number conflict",
                        location={"type": "text_span", "start": c.start, "end": c.end},
                        loc_label=f"Caption {claimed} {unit} ↔ transcript {said} {unit}",
                        raw_score=0.6,
                        method=f"Number + unit pattern in caption vs transcript of {label}",
                        explanation=f"The caption says {claimed} {unit}; the speech in {label} says {said} {unit}.",
                        alternatives=["Transcript error on the number word"], sort=c.start,
                        extra={"target_evidence": label}))

        elif c.kind in ("person", "org") and transcripts:
            joined = " ".join(s["text"] for tr in transcripts.values() for s in tr.get("segments", [])).lower()
            if c.text.lower() in joined:
                c.status, c.detail = "consistent", "named in the transcript"

    ctx.extra["claims"] = [c.to_dict() for c in claims]
    ctx.extra["similarity_backend"] = similarity_backend()
    return findings


def extract_only(ctx: AnalysisContext) -> list[RawFinding]:
    claims: list[Claim] = extract(ctx.original.read_text("utf-8"))
    ctx.extra["claims"] = [c.to_dict() for c in claims]
    ctx.log("text", f"{len(claims)} checkable claims: " + ", ".join(sorted({c.kind for c in claims})) if claims else "no checkable claims")
    return []

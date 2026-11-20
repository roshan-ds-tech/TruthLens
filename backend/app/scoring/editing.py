"""Editing status: was editing detected? Kept separate from the AI-generation assessment.

Derived only from stored findings (family + band) and from whether the checks ran. Never from file names, case titles
or expected labels.

  edited        a content finding (pixels, frames or audio signal) reached "Indicators" or "Strong"
  possible      content findings exist, but all are only inconclusive
  metadata      only metadata findings (software tags, dates, thumbnails); pixels are not shown to be altered
  none          the checks completed and found no indicator; this does not prove the file is untouched
  unavailable   no checks completed (not analysed, or detectors failed or were skipped)
"""
from __future__ import annotations

from typing import Iterable, Optional

LABELS = {
    "edited": "Edited — indicators detected",
    "possible": "Possible editing — inconclusive",
    "metadata": "Metadata changes detected",
    "none": "No editing indicators detected",
    "unavailable": "Editing assessment unavailable",
}
TYPE_NAMES = {
    "copy_move": "Copy-move region", "ela": "Pasted or retouched region", "noise": "Pasted or retouched region",
    "jpeg_ghost": "Pasted or retouched region", "frame_forensics": "Altered frame region",
    "noise_floor": "Audio splice", "band_limit": "Band-limited audio segment", "prosody": "Speech rhythm break",
    "optical_flow": "Cut or missing frames", "frame_dupes": "Duplicated frames", "face_flicker": "Face inconsistency",
    "lipsync": "Lip-sync mismatch", "claim_date": "Caption conflicts with evidence",
    "claim_speech": "Caption conflicts with evidence", "claim_entity": "Caption conflicts with evidence",
    "metadata": "Metadata changes",
}
RANK = {"edited": 4, "possible": 3, "metadata": 2, "unavailable": 1, "none": 0}
SUPPORTED = ("indicators", "strong")


def _types(fams: Iterable[str]) -> list[str]:
    out: list[str] = []
    for f in fams:
        name = TYPE_NAMES.get(f, f.replace("_", " "))
        if name not in out:
            out.append(name)
    return out


def item_status(findings: list[dict], analysed: bool, checks_failed: bool = False) -> dict:
    """findings: dicts with "family" and "band" (AI-generation families are ignored)."""
    fs = [f for f in findings if not f["family"].startswith("ai_") and f.get("band") != "none"]
    content = [f for f in fs if f["family"] != "metadata"]
    meta = [f for f in fs if f["family"] == "metadata"]
    strong = [f for f in content if f["band"] in SUPPORTED]
    if strong:
        key, types = "edited", _types(f["family"] for f in strong)
    elif content:
        key, types = "possible", _types(f["family"] for f in content)
    elif meta:
        key, types = "metadata", _types(["metadata"])
    elif analysed and not checks_failed:
        key, types = "none", []
    else:
        key, types = "unavailable", []
    note = {
        "edited": "Editing checks found supported evidence of a change.",
        "possible": "Some checks reacted, but the evidence is weak or conflicting.",
        "metadata": "File metadata was changed or rewritten. This alone does not show that the picture or sound was altered.",
        "none": "The checks that ran found nothing. This does not prove the file is untouched; some edits leave no trace.",
        "unavailable": "The editing checks did not run or did not complete, so no editing result is available.",
    }[key]
    return {"key": key, "label": LABELS[key], "types": types, "note": note}


def case_status(items: dict[str, dict]) -> dict:
    """Headline = most serious item status; names the evidence that drives it."""
    if not items:
        return {"key": "unavailable", "label": LABELS["unavailable"], "types": [], "items": [],
                "note": "No evidence has been analysed."}
    top = max(RANK[v["key"]] for v in items.values())
    key = next(k for k, r in RANK.items() if r == top)
    drivers = sorted(k for k, v in items.items() if v["key"] == key)
    types: list[str] = []
    for k in drivers:
        types += [t for t in items[k]["types"] if t not in types]
    others = len(items) - len(drivers)
    note = f"{LABELS[key]} in {', '.join(drivers)}" + (f"; {others} other item{'s' if others != 1 else ''} differ." if others else ".")
    return {"key": key, "label": LABELS[key], "types": types, "items": drivers, "note": note}


def from_verdict(findings: list[dict], verdict: Optional[dict], status: str) -> dict:
    """Read-time status for stored evidence (works for older analyses without rewriting them)."""
    analysed = status == "analyzed" and verdict is not None
    failed = bool(verdict) and verdict.get("band") == "inconclusive" and not [
        f for f in findings if not f["family"].startswith("ai_") and f.get("band") != "none"]
    return item_status(findings, analysed, failed)

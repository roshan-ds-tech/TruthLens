"""Checkable claims from a caption or post (§3.6): dates, places, people, organisations, numbers, quotes."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import lru_cache
from typing import Optional

MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE_PATTERNS = [
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}(?:,?\s+\d{{4}})?\b",
    rf"\b{MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b",
]
RELATIVE = {"today": 0, "yesterday": -1, "tonight": 0}
QUOTE_RE = re.compile(r"[\"“”‘’']([^\"“”‘’']{12,})[\"“”‘’']")
NUMBER_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)(?:\s*|-)(day|days|hour|hours|crore|lakh|people|percent|%|km|years?)\b", re.I)
REPORTED_SPEECH = re.compile(r"\b(announc\w*|declar\w*|said|says|stat\w*|told|claims?)\b\s*(?:that\s*)?:?\s*(.+)", re.I)


@dataclass
class Claim:
    kind: str                       # date | place | person | org | number | quote
    text: str
    start: int
    end: int
    value: Optional[str] = None     # ISO date, normalised number…
    relative: bool = False
    status: str = "unverifiable"    # consistent | conflict | unverifiable
    evidence: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=1)
def _nlp():
    try:
        import spacy

        return spacy.load("en_core_web_sm", disable=["lemmatizer"])
    except Exception:
        return None


def extract(text: str, base: Optional[datetime] = None) -> list[Claim]:
    import dateparser

    claims: list[Claim] = []
    taken: list[tuple[int, int]] = []

    def overlaps(a: int, b: int) -> bool:
        return any(a < e and b > s for s, e in taken)

    settings = {"PREFER_DATES_FROM": "past", "REQUIRE_PARTS": ["day", "month"], "DATE_ORDER": "DMY"}
    if base:
        settings["RELATIVE_BASE"] = base
    for pat in DATE_PATTERNS:
        for m in re.finditer(pat, text, re.I):
            if overlaps(m.start(), m.end()):
                continue
            dt = dateparser.parse(m.group(0), settings=settings)
            if dt:
                year_given = bool(re.search(r"\d{4}", m.group(0)))
                if not year_given and base:
                    dt = dt.replace(year=base.year)
                claims.append(Claim("date", m.group(0), m.start(), m.end(), dt.date().isoformat() if (year_given or base) else None))
                taken.append((m.start(), m.end()))
    for word, offset in RELATIVE.items():
        for m in re.finditer(rf"\b{word}\b", text, re.I):
            value = None
            if base:
                from datetime import timedelta

                value = (base + timedelta(days=offset)).date().isoformat()
            claims.append(Claim("date", m.group(0), m.start(), m.end(), value, relative=True))
    for m in QUOTE_RE.finditer(text):
        claims.append(Claim("quote", m.group(1).strip(), m.start(1), m.end(1)))
    if not any(c.kind == "quote" for c in claims):
        m = REPORTED_SPEECH.search(text)
        if m and len(m.group(2).split()) >= 4:
            body = re.split(r"(?<=[.!?])\s", m.group(2))[0].strip()
            claims.append(Claim("quote", body, m.start(2), m.start(2) + len(body), detail="reported speech"))
    for m in NUMBER_RE.finditer(text):
        claims.append(Claim("number", m.group(0), m.start(), m.end(), f"{m.group(1)} {m.group(2).lower()}"))
    nlp = _nlp()
    if nlp is not None:
        kinds = {"GPE": "place", "LOC": "place", "FAC": "place", "PERSON": "person", "ORG": "org"}
        for ent in nlp(text).ents:
            if ent.label_ in kinds and not overlaps(ent.start_char, ent.end_char):
                claims.append(Claim(kinds[ent.label_], ent.text, ent.start_char, ent.end_char))
    else:
        from .gazetteer import PLACES

        for name in PLACES:
            for m in re.finditer(rf"\b{re.escape(name)}\b", text, re.I):
                claims.append(Claim("place", m.group(0), m.start(), m.end()))
    claims.sort(key=lambda c: (c.start, c.kind))
    return claims

"""Signal fusion, confidence ranges and verdict bands (§3.8).

Fusion is a weighted log-odds sum relative to a prior:

    logit(P) = logit(p0) + Σ_f  w_f · (logit(p_f) − logit(p0))      for families with p_f > p0

* one term per method family (the strongest finding in it), so two outputs of the same method are
  never double-counted;
* ``w_f`` comes from ``config.FAMILY_WEIGHTS`` and is halved for findings an R-14-style rule weakens;
* families are added strongest first, the k-th counting 0.6^k, and the result is capped at 0.97;
* absent signals add nothing: TruthLens never treats "no finding" as proof of authenticity;
* the range is the same sum computed on every finding's low and high ends.

Verdict bands on the range [lo, hi]:
    hi < 0.40                         → No indicators found
    lo ≥ 0.70 and corroborated        → Strong indicators
    lo ≥ 0.55                         → Indicators of manipulation
    otherwise (the range touches the middle band) → Inconclusive

Independence rule: "corroborated" needs at least two different method families at p ≥ 0.55, or a
cross-modal *supports* rule linking findings from two different methods.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from .. import config

PRIOR = 0.2
SUPPORT_P = 0.55
DECAY = 0.6       # each further family counts 60% of the previous one
P_MAX = 0.97      # no combination is reported as certain
MIN_HALF_WIDTH = 0.05


@dataclass
class Signal:
    finding_id: str
    family: str
    p: float
    lo: float
    hi: float
    weight_scale: float = 1.0


@dataclass
class Fused:
    p: float
    lo: float
    hi: float
    band: str
    corroborated: bool
    families: list[str]


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _sig(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def _sum(values: dict[str, tuple[float, float]]) -> float:
    """Weighted log-odds sum; the k-th strongest family counts DECAY^k, because forensic signals are
    rarely fully independent and a pile of weak signals must not reach certainty."""
    base = _logit(PRIOR)
    terms = sorted((w * (_logit(p) - base) for p, w in values.values() if p > PRIOR), reverse=True)
    total = base + sum(t * DECAY ** k for k, t in enumerate(terms))
    return min(_sig(total), P_MAX)


def band(lo: float, hi: float, corroborated: bool) -> str:
    if hi < config.BAND_NONE_MAX:
        return "none"
    if lo >= config.BAND_STRONG_MIN and corroborated:
        return "strong"
    if lo >= config.BAND_INDICATORS_MIN:
        return "indicators"
    return "inconclusive"


def finding_band(p: float, lo: float, hi: float) -> str:
    """Band for a single finding. A single signal can never be 'Strong' on its own (independence rule)."""
    return band(lo, hi, corroborated=False)


def fuse(signals: Iterable[Signal], supported_pairs: int = 0) -> Fused:
    best: dict[str, Signal] = {}
    for s in signals:
        if s.family not in best or s.p > best[s.family].p:
            best[s.family] = s
    if not best:
        lo, hi = round(PRIOR - 0.1, 4), round(PRIOR + 0.1, 4)
        return Fused(PRIOR, lo, hi, "none", False, [])
    w = {f: config.FAMILY_WEIGHTS.get(f, 0.5) * s.weight_scale for f, s in best.items()}
    p = _sum({f: (s.p, w[f]) for f, s in best.items()})
    lo = _sum({f: (s.lo, w[f]) for f, s in best.items()})
    hi = _sum({f: (s.hi, w[f]) for f, s in best.items()})
    strong_families = [f for f, s in best.items() if s.p >= SUPPORT_P]
    corroborated = len(strong_families) >= 2 or supported_pairs > 0
    lo, hi = min(lo, p - MIN_HALF_WIDTH), max(hi, min(P_MAX, p + MIN_HALF_WIDTH))   # never a zero-width range
    return Fused(round(p, 4), round(lo, 4), round(hi, 4), band(lo, hi, corroborated),
                 corroborated, sorted(best))

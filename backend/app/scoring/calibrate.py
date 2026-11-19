"""Raw score → calibrated probability and range (§3.8 steps 1 and 3).

``validation/results/calibration.json`` is written by ``make validate``: per indicator, Platt
parameters (A, B) fitted on the seeded test set, plus bootstrap resamples of (A, B). The range is the
10th–90th percentile of the bootstrap probabilities at this raw score. Indicators with too few
validation samples fall back to an uncalibrated identity mapping with a fixed ±0.12 range, and say so.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache

from .. import config


@dataclass(frozen=True)
class Calibrated:
    p: float
    lo: float
    hi: float
    calibrated: bool


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, x))))


@lru_cache(maxsize=1)
def _table() -> dict:
    if config.CALIBRATION_PATH.exists():
        return json.loads(config.CALIBRATION_PATH.read_text())
    return {}


def reload() -> None:
    _table.cache_clear()


P_FLOOR, P_CEIL = 0.02, 0.95   # no single signal is ever reported as certain either way


def _clip(x: float) -> float:
    return round(min(P_CEIL, max(P_FLOOR, x)), 4)


def calibrate(indicator: str, raw: float) -> Calibrated:
    raw = float(max(0.0, min(1.0, raw)))
    entry = _table().get("indicators", {}).get(indicator)
    if not entry or entry.get("n", 0) < 6:
        half = config.DEFAULT_RANGE_HALF_WIDTH
        p = _clip(raw)
        return Calibrated(p, _clip(p - half), _clip(p + half), False)
    p = _sigmoid(entry["A"] * raw + entry["B"])
    boots = sorted(_sigmoid(a * raw + b) for a, b in entry.get("boot", [])) or [p]
    lo = boots[int(0.1 * (len(boots) - 1))]
    hi = boots[int(0.9 * (len(boots) - 1))]
    # never narrower than ±0.04: a small test set cannot justify more precision
    lo, hi = min(lo, p - 0.04), max(hi, p + 0.04)
    return Calibrated(_clip(p), _clip(lo), _clip(hi), True)


def table_version() -> str:
    t = _table()
    return t.get("version", "uncalibrated")

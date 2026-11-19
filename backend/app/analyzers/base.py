"""Analyzer interface (§3): every analyzer takes an evidence item and returns a list of findings.

Analyzers return ``RawFinding``s. IDs, calibrated probabilities, ranges and verdict bands are added
later by the pipeline and scoring, so an analyzer only describes what it observed and where.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Protocol


@dataclass
class RawFinding:
    indicator: str                 # stable machine name, e.g. "ela_inconsistency"
    family: str                    # method family for the independence rule and fusion weights
    name: str                      # human name shown on the card
    location: dict[str, Any]       # matches models.Location
    loc_label: str                 # "00:14.2 · +9 dB jump", "Region 412,220 96×80"
    raw_score: float               # signal strength in [0, 1]; calibrated later
    method: str                    # what was computed, with the key numbers
    explanation: str               # generated from structured evidence, not free text
    alternatives: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)   # file names inside the evidence artifact dir
    extra: dict[str, Any] = field(default_factory=dict)  # e.g. caption-vs-EXIF comparison rows
    sort: float = 0.0              # position (time or y) so IDs are numbered in reading order


@dataclass
class AnalysisContext:
    case_id: str
    evidence_id: int
    label: str                     # "E-01"
    kind: str
    filename: str
    sha256: str
    original: Path                 # read-only original; never written
    derived_dir: Path              # analyzer scratch space (decoded frames, WAV…)
    artifact_dir: Path             # images the UI and the report show
    metadata: dict[str, Any]
    log: Callable[[str, str], None]
    case_evidence: list["AnalysisContext"] = field(default_factory=list)
    shared: dict[str, Any] = field(default_factory=dict)  # per-case results later analyzers read (transcripts…)
    extra: dict[str, Any] = field(default_factory=dict)   # per-evidence outputs stored on the evidence row

    def artifact(self, name: str) -> Path:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        return self.artifact_dir / name


class Analyzer(Protocol):
    key: str          # settings key, e.g. "ela"
    step: str         # label shown in the Analysis progress chips
    kinds: tuple[str, ...]

    def run(self, ctx: AnalysisContext) -> list[RawFinding]: ...


@dataclass
class FnAnalyzer:
    """Adapter so plain functions can be registered as analyzers."""
    key: str
    step: str
    kinds: tuple[str, ...]
    fn: Callable[[AnalysisContext], list[RawFinding]]
    name: str = ""
    desc: str = ""
    version: str = ""
    optional_dep: Optional[str] = None

    def run(self, ctx: AnalysisContext) -> list[RawFinding]:
        return self.fn(ctx)


def fmt_t(t: float) -> str:
    """Seconds → '00:14.2'."""
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m):02d}:{s:04.1f}"


def robust_z(values, center=None):
    """(x − median) / (1.4826·MAD), the outlier score used across analyzers."""
    import numpy as np

    v = np.asarray(values, dtype=np.float64)
    med = np.median(v) if center is None else center
    mad = np.median(np.abs(v - med)) * 1.4826
    if mad < 1e-9:
        mad = max(np.std(v), 1e-9)
    return (v - med) / mad


def squash(x: float, mid: float, scale: float) -> float:
    """Map a raw statistic onto [0, 1] with a logistic curve centred on ``mid``."""
    import math

    return 1.0 / (1.0 + math.exp(-(x - mid) / scale))

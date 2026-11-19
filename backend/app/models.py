"""SQLModel tables (design doc §5.3) and the Pydantic Finding contract (§3.1)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field as PField
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class JsonMixin:
    """Helpers for the *_json text columns."""

    @staticmethod
    def dumps(value: Any) -> str:
        return json.dumps(value, sort_keys=True, ensure_ascii=False)

    @staticmethod
    def loads(value: Optional[str], default: Any = None) -> Any:
        if not value:
            return default
        return json.loads(value)


class Case(SQLModel, table=True):
    __tablename__ = "cases"
    id: str = Field(primary_key=True)                # "C-0007"
    title: str
    description: str = ""
    investigator: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    status: str = "draft"                             # draft | queued | running | analyzed | failed
    closed: bool = False
    overall_verdict_json: Optional[str] = None        # {"band","lo","hi","corroborated","why"}
    limitations_json: Optional[str] = None
    analysis_seconds: Optional[float] = None
    run_count: int = 0


class Evidence(SQLModel, table=True):
    __tablename__ = "evidence"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(index=True, foreign_key="cases.id")
    label: str                                        # "E-01", per case
    kind: str                                         # image | video | audio | text
    filename: str
    sha256: str
    size: int
    mime: str
    metadata_json: str = "{}"
    status: str = "queued"                            # queued | analyzing | analyzed | failed
    parent_id: Optional[int] = None                   # derived evidence (audio track of a video)
    order_idx: int = 0
    verdict_json: Optional[str] = None
    extra_json: Optional[str] = None                  # suspicion curve, waveform peaks, transcript…
    created_at: datetime = Field(default_factory=utcnow)


class FindingRow(SQLModel, table=True):
    __tablename__ = "findings"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(index=True)
    evidence_id: int = Field(index=True, foreign_key="evidence.id")
    finding_id: str                                   # "F-IMG-003"
    modality: str
    indicator: str
    family: str                                       # method family, used by the independence rule
    name: str
    location_json: str
    loc_label: str
    raw_score: float
    score: float                                      # calibrated probability
    conf_low: float
    conf_high: float
    band: str
    method: str
    explanation: str
    alternatives_json: str = "[]"
    artifacts_json: str = "[]"
    extra_json: str = "{}"
    sort_key: str = ""


class Correlation(SQLModel, table=True):
    __tablename__ = "correlations"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(index=True)
    rule_id: str
    rule_name: str
    from_finding: str
    to_finding: str
    relation: str                                     # supports | weakens | conflict
    note: str = ""


class Review(SQLModel, table=True):
    __tablename__ = "reviews"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(index=True)
    finding_id: str                                   # label, so reviews survive a rerun (IDs are stable)
    reviewer: str
    decision: str                                     # accepted | rejected | pending
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class CustodyLog(SQLModel, table=True):
    __tablename__ = "custody_log"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(index=True)
    ts: datetime = Field(default_factory=utcnow)
    actor: str
    action: str
    tool_version: str
    input_hash: str
    output_hash: str
    prev_hash: str                                    # hash chain makes edits detectable
    entry_hash: str


class ReportRow(SQLModel, table=True):
    __tablename__ = "reports"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(index=True)
    path_pdf: Optional[str] = None
    path_json: str
    path_html: str
    sha256: str
    created_at: datetime = Field(default_factory=utcnow)


class Job(SQLModel, table=True):
    __tablename__ = "jobs"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(index=True)
    status: str = "queued"                            # queued | running | done | failed
    created_at: datetime = Field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    progress_json: str = "[]"
    log_json: str = "[]"
    error: Optional[str] = None
    findings_count: int = 0


class Setting(SQLModel, table=True):
    __tablename__ = "settings"
    key: str = Field(primary_key=True)
    value_json: str


# ---------------------------------------------------------------- Finding contract (§3.1)

LocationType = Literal["bbox", "mask", "frame_range", "time_range", "text_span", "file"]


class Location(BaseModel):
    type: LocationType
    x: Optional[int] = None
    y: Optional[int] = None
    w: Optional[int] = None
    h: Optional[int] = None
    image_w: Optional[int] = None
    image_h: Optional[int] = None
    start: Optional[float] = None          # seconds (frame_range, time_range) or char offset (text_span)
    end: Optional[float] = None
    frames: Optional[list[int]] = None
    pair: Optional[dict[str, int]] = None  # copy-move source box
    field: Optional[str] = None            # metadata field name


class ReviewState(BaseModel):
    status: Literal["pending", "accepted", "rejected"] = "pending"
    note: Optional[str] = None


class Finding(BaseModel):
    finding_id: str
    evidence_id: str
    modality: Literal["image", "video", "audio", "text", "cross-modal"]
    indicator: str
    location: Location
    score: float
    confidence_range: tuple[float, float]
    method: str
    explanation: str
    alternatives: list[str] = PField(default_factory=list)
    artifacts: list[str] = PField(default_factory=list)
    review: ReviewState = PField(default_factory=ReviewState)

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "validation"))

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """Fresh, isolated storage and database for each test."""
    from app import config, db

    config.set_data_dir(tmp_path / "data")
    db.reset_engine()
    yield tmp_path / "data"
    db.reset_engine()


@pytest.fixture()
def client(data_dir):
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


def make_ctx(path: Path, kind: str, tmp: Path | None = None, label: str = "E-01"):
    from app.analyzers.base import AnalysisContext
    from app.ingest.metadata import av_metadata, image_metadata

    tmp = tmp or Path(tempfile.mkdtemp())
    meta = image_metadata(path) if kind == "image" else av_metadata(path) if kind in ("audio", "video") else {}
    return AnalysisContext("C-TEST", 1, label, kind, path.name, "0" * 64, path, tmp / "derived", tmp / "artifacts", meta,
                           lambda src, msg: None)


def iou(box: dict, mask: np.ndarray) -> float:
    m = np.zeros_like(mask)
    m[box["y"]:box["y"] + box["h"], box["x"]:box["x"] + box["w"]] = True
    return float((m & mask).sum() / max((m | mask).sum(), 1))


def upload(client, case_id: str, name: str):
    with open(FIXTURES / name, "rb") as f:
        return client.post(f"/api/cases/{case_id}/evidence", files={"file": (name, f, "application/octet-stream")})


def run_analysis(client, case_id: str, timeout: float = 600) -> dict:
    from app import jobs

    r = client.post(f"/api/cases/{case_id}/analyze")
    assert r.status_code == 200, r.text
    jobs.wait(r.json()["job_id"], timeout)
    job = client.get(f"/api/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job

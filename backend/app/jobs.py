"""Background job queue: one worker thread, so only one analysis holds RAM at a time (§2, §6)."""
from __future__ import annotations

import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional

from sqlmodel import select

from . import db, pipeline
from .models import Case, Job, JsonMixin, utcnow

_executor: Optional[ThreadPoolExecutor] = None
_futures: dict[int, Future] = {}


def executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="truthlens-analysis")
    return _executor


def _work(job_id: int, actor: str) -> None:
    with db.session() as s:
        job = s.get(Job, job_id)
        try:
            pipeline.run_case(s, job.case_id, job, actor)
        except Exception as exc:  # noqa: BLE001 - report the failure on the job, never crash the worker
            traceback.print_exc()
            s.rollback()
            job = s.get(Job, job_id)
            job.status, job.finished_at, job.error = "failed", utcnow(), f"{exc.__class__.__name__}: {pipeline._scrub(str(exc))}"
            lines = JsonMixin.loads(job.log_json, [])
            lines.append({"t": utcnow().strftime("%H:%M:%S.000"), "src": "run", "msg": f"failed · {job.error}"})
            job.log_json = JsonMixin.dumps(lines)
            case = s.get(Case, job.case_id)
            if case:
                case.status = "failed"
                s.add(case)
            s.add(job)
            s.commit()


def submit(case_id: str, actor: str) -> Job:
    with db.session() as s:
        running = s.exec(select(Job).where(Job.case_id == case_id, Job.status.in_(["queued", "running"]))).first()  # type: ignore[attr-defined]
        if running:
            return running
        job = Job(case_id=case_id)
        s.add(job)
        case = s.get(Case, case_id)
        case.status = "queued"
        s.add(case)
        s.commit()
        s.refresh(job)
    _futures[job.id] = executor().submit(_work, job.id, actor)
    return job


def wait(job_id: int, timeout: Optional[float] = None) -> None:
    """Block until a job finishes (CLI and tests)."""
    fut = _futures.get(job_id)
    if fut is not None:
        fut.result(timeout=timeout)

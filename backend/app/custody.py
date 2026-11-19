"""Chain of custody: SHA-256 hashing, the read-only original store and the append-only log (§3.2)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any, Iterable

from sqlmodel import Session, select

from . import config
from .models import CustodyLog, utcnow

GENESIS = "0" * 64


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj: Any) -> str:
    """Hash of a canonical JSON encoding, used for findings and reviews."""
    return sha256_bytes(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def short(h: str) -> str:
    """'9f2c41a7…e81b', the form the UI shows."""
    return f"{h[:8]}…{h[-4:]}" if len(h) >= 12 else h


def store_original(case_id: str, src: Path, sha: str, ext: str) -> Path:
    """Copy an upload to evidence/<case>/<sha>/original.<ext> and make it read-only."""
    dest_dir = config.EVIDENCE_DIR / case_id / sha
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"original.{ext}"
    if not dest.exists():
        shutil.copyfile(src, dest)
        os.chmod(dest, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    if sha256_file(dest) != sha:
        raise RuntimeError(f"stored original {dest} does not match its hash")
    return dest


def original_path(case_id: str, sha: str) -> Path:
    matches = sorted((config.EVIDENCE_DIR / case_id / sha).glob("original.*"))
    if not matches:
        raise FileNotFoundError(f"original for {sha} missing")
    return matches[0]


def verify_original(case_id: str, sha: str) -> bool:
    p = original_path(case_id, sha)
    return sha256_file(p) == sha and not os.access(p, os.W_OK)


def _entry_hash(prev: str, case_id: str, ts: str, actor: str, action: str, tool: str, inp: str, out: str) -> str:
    return sha256_bytes("|".join([prev, case_id, ts, actor, action, tool, inp, out]).encode())


def log(s: Session, case_id: str, actor: str, action: str, tool_version: str,
        input_hash: str = "—", output_hash: str = "—") -> CustodyLog:
    """Append one entry. Each entry hashes the previous one, so any edit breaks the chain."""
    last = s.exec(select(CustodyLog).where(CustodyLog.case_id == case_id)
                  .order_by(CustodyLog.id.desc())).first()  # type: ignore[union-attr]
    prev = last.entry_hash if last else GENESIS
    ts = utcnow()
    entry = CustodyLog(case_id=case_id, ts=ts, actor=actor, action=action, tool_version=tool_version,
                       input_hash=input_hash, output_hash=output_hash, prev_hash=prev,
                       entry_hash=_entry_hash(prev, case_id, ts.isoformat(), actor, action, tool_version,
                                              input_hash, output_hash))
    s.add(entry)
    s.commit()
    s.refresh(entry)
    return entry


def entries(s: Session, case_id: str) -> list[CustodyLog]:
    return list(s.exec(select(CustodyLog).where(CustodyLog.case_id == case_id).order_by(CustodyLog.id)))


def verify_chain(rows: Iterable[CustodyLog]) -> bool:
    prev = GENESIS
    for r in rows:
        ts = r.ts.replace(tzinfo=r.ts.tzinfo or utcnow().tzinfo).isoformat()
        if r.prev_hash != prev or r.entry_hash != _entry_hash(prev, r.case_id, ts, r.actor, r.action,
                                                              r.tool_version, r.input_hash, r.output_hash):
            return False
        prev = r.entry_hash
    return True

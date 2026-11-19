"""SQLite engine and session helpers."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import event, text
from sqlmodel import Session, SQLModel, create_engine

from . import config

_engine = None


def engine():
    global _engine
    if _engine is None:
        config.ensure_dirs()
        _engine = create_engine(f"sqlite:///{config.DB_PATH}", connect_args={"check_same_thread": False})

        @event.listens_for(_engine, "connect")
        def _pragmas(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        init_db(_engine)
    return _engine


def init_db(eng) -> None:
    from . import models  # noqa: F401  (registers tables)

    SQLModel.metadata.create_all(eng)
    with eng.begin() as conn:
        # databases created before accounts existed: add the owner column in place
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(cases)"))]
        if "owner_id" not in cols:
            conn.execute(text("ALTER TABLE cases ADD COLUMN owner_id INTEGER"))
        # The custody log is append-only: the database itself refuses edits and deletes.
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS custody_no_update BEFORE UPDATE ON custody_log "
            "BEGIN SELECT RAISE(ABORT, 'custody_log is append-only'); END;"))
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS custody_no_delete BEFORE DELETE ON custody_log "
            "BEGIN SELECT RAISE(ABORT, 'custody_log is append-only'); END;"))


def reset_engine() -> None:
    """Drop the cached engine (tests point TRUTHLENS_DATA at a temp dir)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


@contextmanager
def session() -> Iterator[Session]:
    with Session(engine(), expire_on_commit=False) as s:
        yield s

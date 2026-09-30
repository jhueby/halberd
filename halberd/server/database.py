from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATA_DIR = Path(os.environ.get("HALBERD_DATA_DIR", os.path.expanduser("~/.halberd")))


class Base(DeclarativeBase):
    pass


def get_engine(db_path: Path | None = None):
    if db_path is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        db_path = DATA_DIR / "halberd.db"
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session_factory(engine=None) -> sessionmaker[Session]:
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)


def _ensure_columns(engine) -> None:
    # Additive migrations for existing SQLite DBs — create_all() makes missing
    # tables but never adds columns to an existing one.
    from sqlalchemy import text
    wanted = {"agents": {"version": "VARCHAR(32)"}}
    with engine.begin() as conn:
        for table, cols in wanted.items():
            have = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for col, decl in cols.items():
                if col not in have:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {decl}"))


def init_db(engine=None) -> None:
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    _ensure_columns(engine)

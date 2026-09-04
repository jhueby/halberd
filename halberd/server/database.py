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


def init_db(engine=None) -> None:
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)

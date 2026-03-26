"""Database setup and savepoint-based transaction manager for the environment."""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./env.db")
is_sqlite = DATABASE_URL.startswith("sqlite")

engine_args = {"echo": False}
if is_sqlite:
    engine_args["connect_args"] = {"check_same_thread": False, "timeout": 30}
    engine_args["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class TransactionManager:
    """Manage per-episode savepoints for deterministic Env resets."""

    def __init__(self):
        self._session: Optional[Session] = None
        self._savepoint = None

    def begin_episode(self) -> None:
        """Start a new nested transaction (savepoint) and keep the session alive."""
        session = SessionLocal()
        self._savepoint = session.begin_nested()
        self._session = session

    def rollback_episode(self) -> None:
        """Rollback the current savepoint and close the session if one exists."""
        if self._session is None:
            return

        session = self._session
        try:
            session.rollback()
        finally:
            session.close()
            self._session = None
            self._savepoint = None

    def get_session(self) -> Session:
        """
        Return the active session if an episode is in progress.

        Raises RuntimeError when called before `begin_episode()` to maintain the
        contract that all interactions happen inside a savepoint/session combo.
        """
        if self._session is None:
            raise RuntimeError("No active episode. Call begin_episode() first.")
        return self._session

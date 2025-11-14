"""Unit of Work for coordinating repository operations.

This implementation provides a context manager that owns a SQLAlchemy
Session by default (via `researcharr.storage.database.get_session()`)
so that multiple repository operations can be performed atomically with
centralized commit/rollback. An external Session can also be supplied
for composition in higher-level transactions.
"""

from __future__ import annotations

from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from researcharr.repositories.global_settings import GlobalSettingsRepository
from researcharr.repositories.managed_app import ManagedAppRepository
from researcharr.repositories.processing_log import ProcessingLogRepository
from researcharr.repositories.search_cycle import SearchCycleRepository
from researcharr.repositories.tracked_item import TrackedItemRepository
from researcharr.storage.database import get_session


class UnitOfWork(AbstractContextManager["UnitOfWork"]):
    """Coordinates a transactional set of repository operations."""

    def __init__(self, session: Session | None = None):
        self._external_session = session
        self._session: Session | None = None
        self._ctx = None
        # Lazy-initialized repositories bound to the active session
        self._apps: ManagedAppRepository | None = None
        self._items: TrackedItemRepository | None = None
        self._logs: ProcessingLogRepository | None = None
        self._cycles: SearchCycleRepository | None = None
        self._settings: GlobalSettingsRepository | None = None

    # Context manager protocol
    def __enter__(self) -> UnitOfWork:
        if self._external_session is not None:
            self._session = self._external_session
        else:
            # Acquire managed session context
            self._ctx = get_session()
            self._session = self._ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # Delegate commit/rollback/close to the managed context when we own it
        if self._ctx is not None:
            try:
                self._ctx.__exit__(exc_type, exc, tb)
            finally:
                self._ctx = None
                self._session = None

    # Session access
    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active. Use 'with UnitOfWork() as uow:'")
        return self._session

    # Repository accessors (lazy)
    @property
    def apps(self) -> ManagedAppRepository:
        if self._apps is None:
            self._apps = ManagedAppRepository(self.session)
        return self._apps

    @property
    def items(self) -> TrackedItemRepository:
        if self._items is None:
            self._items = TrackedItemRepository(self.session)
        return self._items

    @property
    def logs(self) -> ProcessingLogRepository:
        if self._logs is None:
            self._logs = ProcessingLogRepository(self.session)
        return self._logs

    @property
    def cycles(self) -> SearchCycleRepository:
        if self._cycles is None:
            self._cycles = SearchCycleRepository(self.session)
        return self._cycles

    @property
    def settings(self) -> GlobalSettingsRepository:
        if self._settings is None:
            self._settings = GlobalSettingsRepository(self.session)
        return self._settings

    # Optional explicit commit for external sessions
    def commit(self) -> None:
        if self._session is not None and self._external_session is not None:
            self._session.commit()

    def rollback(self) -> None:
        if self._session is not None and self._external_session is not None:
            self._session.rollback()


__all__ = ["UnitOfWork"]

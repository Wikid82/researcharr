"""Protocol interfaces for repository abstractions.

These protocols describe the surface area consumed by higher layers
(services, API handlers). They enable structural typing so tests or
alternative implementations (e.g., in-memory fakes) can be supplied
without tightly coupling to concrete SQLAlchemy code.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session

from researcharr.storage.models import (
    AppType,
    CyclePhase,
    GlobalSettings,
    ManagedApp,
    ProcessingLog,
    SearchCycle,
    SortStrategy,
    TrackedItem,
)


@runtime_checkable
class SupportsSession(Protocol):
    """Protocol for objects that expose a SQLAlchemy Session."""

    session: Session


@runtime_checkable
class IGlobalSettingsRepository(Protocol):
    def get_or_create(self) -> GlobalSettings: ...  # noqa: D401
    def get_by_id(self, id: int) -> GlobalSettings | None: ...
    def update(self, entity: GlobalSettings) -> GlobalSettings: ...


@runtime_checkable
class IManagedAppRepository(Protocol):
    def get_by_id(self, id: int) -> ManagedApp | None: ...
    def get_all(self) -> Sequence[ManagedApp]: ...
    def get_active_apps(self) -> Sequence[ManagedApp]: ...
    def get_by_type(self, app_type: AppType) -> Sequence[ManagedApp]: ...
    def get_by_url(self, base_url: str, app_type: AppType) -> ManagedApp | None: ...
    def create(self, entity: ManagedApp) -> ManagedApp: ...
    def update(self, entity: ManagedApp) -> ManagedApp: ...
    def delete(self, id: int) -> bool: ...


@runtime_checkable
class ITrackedItemRepository(Protocol):
    def get_by_id(self, id: int) -> TrackedItem | None: ...
    def get_by_app(self, app_id: int) -> Sequence[TrackedItem]: ...
    def get_by_arr_id(self, app_id: int, arr_id: int) -> TrackedItem | None: ...
    def get_items_for_search(
        self, app_id: int, sort_strategy: SortStrategy, limit: int, include_retries: bool = True
    ) -> Sequence[TrackedItem]: ...
    def get_retry_queue_size(self, app_id: int) -> int: ...
    def mark_searched(
        self, item_id: int, success: bool, next_retry_at: datetime | None = None
    ) -> TrackedItem | None: ...
    def create(self, entity: TrackedItem) -> TrackedItem: ...
    def update(self, entity: TrackedItem) -> TrackedItem: ...


@runtime_checkable
class ISearchCycleRepository(Protocol):
    def get_latest_cycle(self, app_id: int) -> SearchCycle | None: ...
    def get_active_cycle(self, app_id: int) -> SearchCycle | None: ...
    def create_cycle(self, app_id: int) -> SearchCycle: ...
    def update_phase(self, cycle_id: int, phase: CyclePhase) -> SearchCycle | None: ...
    def complete_cycle(self, cycle_id: int, next_cycle_at: datetime) -> SearchCycle | None: ...


@runtime_checkable
class IProcessingLogRepository(Protocol):
    def log_event(
        self,
        app_id: int,
        event_type: str,
        message: str,
        success: bool = True,
        details: str | None = None,
        tracked_item_id: int | None = None,
    ) -> ProcessingLog: ...
    def cleanup_old_logs(self, days: int = 30) -> int: ...
    def get_by_app(self, app_id: int, limit: int = 100) -> Sequence[ProcessingLog]: ...
    def get_by_tracked_item(self, tracked_item_id: int) -> Sequence[ProcessingLog]: ...
    def get_by_event_type(
        self, app_id: int, event_type: str, limit: int = 50
    ) -> Sequence[ProcessingLog]: ...


__all__ = [
    "SupportsSession",
    "IGlobalSettingsRepository",
    "IManagedAppRepository",
    "ITrackedItemRepository",
    "ISearchCycleRepository",
    "IProcessingLogRepository",
]

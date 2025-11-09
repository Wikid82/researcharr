"""Type stubs for SQLAlchemy models.

This file provides type hints for SQLAlchemy model attributes to help type checkers
understand that Column attributes can be assigned regular Python values.
"""

from datetime import datetime

from sqlalchemy.orm import Mapped

from researcharr.storage.models import (
    CyclePhase,
    SearchCycle,
    TrackedItem,
)

# Extend model classes with proper type hints for assignment
class TrackedItem:
    search_count: Mapped[int]
    last_search_at: Mapped[datetime | None]
    failed_search_count: Mapped[int]
    next_retry_at: Mapped[datetime | None]

class SearchCycle:
    phase: Mapped[CyclePhase]
    completed_at: Mapped[datetime | None]
    next_cycle_at: Mapped[datetime | None]

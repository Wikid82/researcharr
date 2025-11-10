"""Repository for SearchCycle model."""

from datetime import datetime

from researcharr.storage.models import CyclePhase, SearchCycle

from .base import BaseRepository


class SearchCycleRepository(BaseRepository[SearchCycle]):
    """Repository for managing search cycle records."""

    def get_by_id(self, id: int) -> SearchCycle | None:
        """Get search cycle by ID."""
        return self.session.query(SearchCycle).filter(SearchCycle.id == id).first()

    def get_all(self) -> list[SearchCycle]:
        """Get all search cycles."""
        return self.session.query(SearchCycle).all()

    def create(self, entity: SearchCycle) -> SearchCycle:
        """Create new search cycle."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity: SearchCycle) -> SearchCycle:
        """Update existing search cycle."""
        self.session.merge(entity)
        self.session.flush()
        return entity

    def delete(self, id: int) -> bool:
        """Delete search cycle by ID."""
        cycle = self.get_by_id(id)
        if cycle:
            self.session.delete(cycle)
            self.session.flush()
            return True
        return False

    def get_by_app(self, app_id: int) -> list[SearchCycle]:
        """
        Get all search cycles for a specific app.

        Args:
            app_id: ManagedApp ID

        Returns:
            List of SearchCycle instances
        """
        return (
            self.session.query(SearchCycle)
            .filter(SearchCycle.app_id == app_id)
            .order_by(SearchCycle.cycle_number.desc())
            .all()
        )

    def get_latest_cycle(self, app_id: int) -> SearchCycle | None:
        """
        Get the most recent search cycle for an app.

        Args:
            app_id: ManagedApp ID

        Returns:
            Latest SearchCycle or None
        """
        return (
            self.session.query(SearchCycle)
            .filter(SearchCycle.app_id == app_id)
            .order_by(SearchCycle.cycle_number.desc())
            .first()
        )

    def get_active_cycle(self, app_id: int) -> SearchCycle | None:
        """
        Get the currently active (incomplete) cycle for an app.

        Args:
            app_id: ManagedApp ID

        Returns:
            Active SearchCycle or None
        """
        return (
            self.session.query(SearchCycle)
            .filter(SearchCycle.app_id == app_id, SearchCycle.completed_at.is_(None))
            .first()
        )

    def create_cycle(self, app_id: int) -> SearchCycle:
        """
        Create a new search cycle for an app.

        Args:
            app_id: ManagedApp ID

        Returns:
            New SearchCycle instance
        """
        latest = self.get_latest_cycle(app_id)
        next_cycle_number = (latest.cycle_number + 1) if latest else 1

        cycle = SearchCycle(
            app_id=app_id,
            cycle_number=next_cycle_number,
            phase=CyclePhase.SYNCING,
            started_at=datetime.utcnow(),
        )
        self.session.add(cycle)
        self.session.flush()
        return cycle

    def update_phase(self, cycle_id: int, phase: CyclePhase) -> SearchCycle | None:
        """
        Update cycle phase.

        Args:
            cycle_id: SearchCycle ID
            phase: New phase

        Returns:
            Updated SearchCycle or None
        """
        cycle = self.get_by_id(cycle_id)
        if cycle:
            cycle.phase = phase
            self.session.flush()
        return cycle

    def complete_cycle(self, cycle_id: int, next_cycle_at: datetime) -> SearchCycle | None:
        """
        Mark cycle as completed.

        Args:
            cycle_id: SearchCycle ID
            next_cycle_at: When the next cycle should start

        Returns:
            Updated SearchCycle or None
        """
        cycle = self.get_by_id(cycle_id)
        if cycle:
            cycle.completed_at = datetime.utcnow()
            cycle.next_cycle_at = next_cycle_at
            self.session.flush()
        return cycle

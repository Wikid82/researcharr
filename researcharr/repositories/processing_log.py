"""Repository for ProcessingLog model."""

from datetime import datetime, timedelta

from researcharr.storage.models import ProcessingLog

from .base import BaseRepository


class ProcessingLogRepository(BaseRepository[ProcessingLog]):
    """Repository for managing processing logs."""

    def get_by_id(self, id: int) -> ProcessingLog | None:
        """Get processing log by ID."""
        return self.session.query(ProcessingLog).filter(ProcessingLog.id == id).first()

    def get_all(self) -> list[ProcessingLog]:
        """Get all processing logs."""
        return self.session.query(ProcessingLog).all()

    def create(self, entity: ProcessingLog) -> ProcessingLog:
        """Create new processing log."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity: ProcessingLog) -> ProcessingLog:
        """Update existing processing log."""
        self.session.merge(entity)
        self.session.flush()
        return entity

    def delete(self, id: int) -> bool:
        """Delete processing log by ID."""
        log = self.get_by_id(id)
        if log:
            self.session.delete(log)
            self.session.flush()
            return True
        return False

    def get_by_app(self, app_id: int, limit: int = 100) -> list[ProcessingLog]:
        """
        Get recent processing logs for a specific app.

        Args:
            app_id: ManagedApp ID
            limit: Maximum number of logs to return

        Returns:
            List of ProcessingLog instances
        """
        return (
            self.session.query(ProcessingLog)
            .filter(ProcessingLog.app_id == app_id)
            .order_by(ProcessingLog.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_tracked_item(self, tracked_item_id: int) -> list[ProcessingLog]:
        """
        Get all logs for a specific tracked item.

        Args:
            tracked_item_id: TrackedItem ID

        Returns:
            List of ProcessingLog instances
        """
        return (
            self.session.query(ProcessingLog)
            .filter(ProcessingLog.tracked_item_id == tracked_item_id)
            .order_by(ProcessingLog.created_at.desc())
            .all()
        )

    def get_by_event_type(
        self, app_id: int, event_type: str, limit: int = 50
    ) -> list[ProcessingLog]:
        """
        Get logs by event type for an app.

        Args:
            app_id: ManagedApp ID
            event_type: Event type to filter by
            limit: Maximum number of logs to return

        Returns:
            List of ProcessingLog instances
        """
        return (
            self.session.query(ProcessingLog)
            .filter(ProcessingLog.app_id == app_id, ProcessingLog.event_type == event_type)
            .order_by(ProcessingLog.created_at.desc())
            .limit(limit)
            .all()
        )

    def log_event(
        self,
        app_id: int,
        event_type: str,
        message: str,
        success: bool = True,
        details: str | None = None,
        tracked_item_id: int | None = None,
    ) -> ProcessingLog:
        """
        Create a new log entry.

        Args:
            app_id: ManagedApp ID
            event_type: Type of event
            message: Log message
            success: Whether event was successful
            details: Additional details (optional)
            tracked_item_id: Related TrackedItem ID (optional)

        Returns:
            Created ProcessingLog instance
        """
        log = ProcessingLog(
            app_id=app_id,
            tracked_item_id=tracked_item_id,
            event_type=event_type,
            message=message,
            details=details,
            success=success,
            created_at=datetime.utcnow(),
        )
        self.session.add(log)
        self.session.flush()
        return log

    def cleanup_old_logs(self, days: int = 30) -> int:
        """
        Delete logs older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of logs deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = (
            self.session.query(ProcessingLog)
            .filter(ProcessingLog.created_at < cutoff_date)
            .delete()
        )
        self.session.flush()
        return deleted

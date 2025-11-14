"""Repository for ProcessingLog model."""

from datetime import datetime, timedelta

from sqlalchemy import func

from researcharr.cache import get as cache_get
from researcharr.cache import invalidate as cache_invalidate
from researcharr.cache import (
    make_key,
)
from researcharr.cache import set as cache_set
from researcharr.repositories.exceptions import ValidationError
from researcharr.storage.models import ProcessingLog
from researcharr.validators import validate_processing_log

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
        # basedpyright: reportAttributeAccessIssue=false
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
        try:
            validate_processing_log(log)
        except ValidationError:
            raise
        self.session.add(log)
        self.session.flush()
        # Invalidate cached aggregates for this app
        prefix = make_key(("ProcessingLog", "", app_id))
        cache_invalidate(prefix)
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
        if deleted:
            prefix = make_key(("ProcessingLog", "", ""))
            cache_invalidate(prefix)
        return deleted

    def get_event_counts(self, app_id: int, since: datetime | None = None) -> dict[str, int]:
        """Return counts of events by type for an app, optionally since a timestamp.

        Cached with small TTL; since timestamp is bucketed to 60s to limit key churn.
        """
        bucket: int | str
        if since is not None:
            # floor to minute boundaries for key stability
            bucket = int(since.timestamp() // 60)
        else:
            bucket = "all"
        key = make_key(("ProcessingLog", "counts", app_id, bucket))
        cached = cache_get(key)
        if cached is not None:
            return cached
        q = self.session.query(ProcessingLog.event_type, func.count(ProcessingLog.id)).filter(
            ProcessingLog.app_id == app_id
        )
        if since is not None:
            q = q.filter(ProcessingLog.created_at >= since)
        rows = q.group_by(ProcessingLog.event_type).all()
        result = {etype: int(count) for etype, count in rows}
        cache_set(key, result, ttl=30)
        return result

    def get_success_rate(self, app_id: int, since: datetime | None = None) -> float:
        """Return fraction of successful events for an app (0.0-1.0).

        Cached using same 60s bucket strategy as event counts.
        """
        bucket: int | str
        if since is not None:
            bucket = int(since.timestamp() // 60)
        else:
            bucket = "all"
        key = make_key(("ProcessingLog", "success_rate", app_id, bucket))
        cached = cache_get(key)
        if cached is not None:
            return cached
        q_total = self.session.query(func.count(ProcessingLog.id)).filter(
            ProcessingLog.app_id == app_id
        )
        q_success = self.session.query(func.count(ProcessingLog.id)).filter(
            ProcessingLog.app_id == app_id, ProcessingLog.success.is_(True)
        )
        if since is not None:
            q_total = q_total.filter(ProcessingLog.created_at >= since)
            q_success = q_success.filter(ProcessingLog.created_at >= since)
        total = int(q_total.scalar() or 0)
        if total == 0:
            cache_set(key, 0.0, ttl=30)
            return 0.0
        success = int(q_success.scalar() or 0)
        rate = success / total
        cache_set(key, rate, ttl=30)
        return rate

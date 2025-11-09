"""Repository for TrackedItem model."""

from datetime import datetime

from sqlalchemy import and_, or_

from researcharr.storage.models import SortStrategy, TrackedItem

from .base import BaseRepository


class TrackedItemRepository(BaseRepository[TrackedItem]):
    """Repository for managing tracked media items."""

    def get_by_id(self, id: int) -> TrackedItem | None:
        """Get tracked item by ID."""
        return self.session.query(TrackedItem).filter(TrackedItem.id == id).first()

    def get_all(self) -> list[TrackedItem]:
        """Get all tracked items."""
        return self.session.query(TrackedItem).all()

    def create(self, entity: TrackedItem) -> TrackedItem:
        """Create new tracked item."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity: TrackedItem) -> TrackedItem:
        """Update existing tracked item."""
        self.session.merge(entity)
        self.session.flush()
        return entity

    def delete(self, id: int) -> bool:
        """Delete tracked item by ID."""
        item = self.get_by_id(id)
        if item:
            self.session.delete(item)
            self.session.flush()
            return True
        return False

    def get_by_app(self, app_id: int) -> list[TrackedItem]:
        """
        Get all tracked items for a specific app.

        Args:
            app_id: ManagedApp ID

        Returns:
            List of TrackedItem instances
        """
        return self.session.query(TrackedItem).filter(TrackedItem.app_id == app_id).all()

    def get_by_arr_id(self, app_id: int, arr_id: int) -> TrackedItem | None:
        """
        Get tracked item by app and Sonarr/Radarr ID.

        Args:
            app_id: ManagedApp ID
            arr_id: ID in Sonarr/Radarr

        Returns:
            TrackedItem instance or None
        """
        return (
            self.session.query(TrackedItem)
            .filter(TrackedItem.app_id == app_id, TrackedItem.arr_id == arr_id)
            .first()
        )

    def get_items_for_search(
        self,
        app_id: int,
        sort_strategy: SortStrategy,
        limit: int,
        include_retries: bool = True,
    ) -> list[TrackedItem]:
        """
        Get items that need searching, sorted by strategy.

        Args:
            app_id: ManagedApp ID
            sort_strategy: How to sort items
            limit: Maximum number of items to return
            include_retries: Whether to include items in retry queue

        Returns:
            List of TrackedItem instances ready for search
        """
        query = self.session.query(TrackedItem).filter(
            TrackedItem.app_id == app_id,
            TrackedItem.monitored,
            ~TrackedItem.has_file,
        )

        # Handle retry queue filtering
        if include_retries:
            # Include items never searched OR items ready for retry
            query = query.filter(
                or_(
                    TrackedItem.last_search_at.is_(None),
                    and_(
                        TrackedItem.next_retry_at.isnot(None),
                        TrackedItem.next_retry_at <= datetime.utcnow(),
                    ),
                )
            )
        else:
            # Exclude items in retry queue
            query = query.filter(TrackedItem.last_search_at.is_(None))

        # Apply sort strategy
        if sort_strategy == SortStrategy.CUSTOM_FORMAT_SCORE_ASC:
            query = query.order_by(TrackedItem.custom_format_score.asc())
        elif sort_strategy == SortStrategy.CUSTOM_FORMAT_SCORE_DESC:
            query = query.order_by(TrackedItem.custom_format_score.desc())
        elif sort_strategy == SortStrategy.ALPHABETICAL_ASC:
            query = query.order_by(TrackedItem.title.asc())
        elif sort_strategy == SortStrategy.ALPHABETICAL_DESC:
            query = query.order_by(TrackedItem.title.desc())
        elif sort_strategy == SortStrategy.EXTERNAL_ID_ASC:
            # App-aware: prioritize TMDB for Radarr, TVDB for Sonarr
            from sqlalchemy import func

            query = query.order_by(func.coalesce(TrackedItem.tmdb_id, TrackedItem.tvdb_id).asc())
        elif sort_strategy == SortStrategy.EXTERNAL_ID_DESC:
            from sqlalchemy import func

            query = query.order_by(func.coalesce(TrackedItem.tmdb_id, TrackedItem.tvdb_id).desc())
        elif sort_strategy == SortStrategy.RANDOM:
            # SQLite-specific random ordering
            from sqlalchemy import func

            query = query.order_by(func.random())

        return query.limit(limit).all()

    def get_retry_queue_size(self, app_id: int) -> int:
        """
        Get count of items currently in retry queue.

        Args:
            app_id: ManagedApp ID

        Returns:
            Number of items waiting for retry
        """
        return (
            self.session.query(TrackedItem)
            .filter(
                TrackedItem.app_id == app_id,
                TrackedItem.next_retry_at.isnot(None),
                TrackedItem.next_retry_at <= datetime.utcnow(),
            )
            .count()
        )

    def mark_searched(
        self, item_id: int, success: bool, next_retry_at: datetime | None = None
    ) -> TrackedItem | None:
        """
        Update item after search attempt.

        Args:
            item_id: TrackedItem ID
            success: Whether search succeeded
            next_retry_at: When to retry if failed (None if not retrying)

        Returns:
            Updated TrackedItem or None if not found
        """
        item = self.get_by_id(item_id)
        if not item:
            return None

        item.search_count += 1
        item.last_search_at = datetime.utcnow()

        if not success:
            item.failed_search_count += 1
            item.next_retry_at = next_retry_at
        else:
            # Reset failure state on success
            item.failed_search_count = 0
            item.next_retry_at = None

        self.session.flush()
        return item

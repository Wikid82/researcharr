"""Base repository interface.

Adds common optional helpers for bulk operations and simple pagination.
Concrete repositories may use these directly without overriding.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository providing common CRUD operations.

    All concrete repositories should inherit from this class and implement
    the required methods.
    """

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    @abstractmethod
    def get_by_id(self, id: int) -> T | None:
        """
        Get entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity instance or None if not found
        """
        pass

    @abstractmethod
    def get_all(self) -> list[T]:
        """
        Get all entities.

        Returns:
            List of all entity instances
        """
        pass

    @abstractmethod
    def create(self, entity: T) -> T:
        """
        Create new entity.

        Args:
            entity: Entity instance to create

        Returns:
            Created entity with ID populated
        """
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """
        Update existing entity.

        Args:
            entity: Entity instance to update

        Returns:
            Updated entity
        """
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Entity ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    # Optional helpers (non-abstract)
    def bulk_create(self, entities: list[T]) -> list[T]:
        """Persist a list of new entities efficiently.

        Args:
            entities: List of transient entity instances.
        Returns:
            Same list with primary keys populated after flush.
        """
        if not entities:
            return entities
        self.session.add_all(entities)
        self.session.flush()
        return entities

    def bulk_upsert(self, entities: list[T]) -> list[T]:
        """Upsert a collection of entities (merge semantics per instance).

        Args:
            entities: List of detached or transient entities.
        Returns:
            List of managed (merged) entities after flush.
        """
        if not entities:
            return entities
        merged: list[T] = []
        for e in entities:
            merged.append(self.session.merge(e))  # type: ignore[arg-type]
        self.session.flush()
        return merged

    def paginate(self, model_cls, page: int, page_size: int) -> list[T]:
        """Return a page of rows for the given mapped class.

        This generic helper requires the concrete repository to supply the
        mapped class when calling. It avoids storing model type state in the
        base class while still offering a shared pagination helper.

        Args:
            model_cls: SQLAlchemy declarative model class.
            page: 1-based page number.
            page_size: Number of rows per page.
        Returns:
            List of entities for the requested page.
        """
        page = max(page, 1)
        offset = (page - 1) * page_size
        return (
            self.session.query(model_cls)  # type: ignore[arg-type]
            .offset(offset)
            .limit(page_size)
            .all()
        )

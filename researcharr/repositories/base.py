"""Base repository interface."""

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

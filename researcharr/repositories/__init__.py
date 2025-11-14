"""Repository interfaces and implementations."""

from .base import BaseRepository
from .exceptions import (
    ConflictError,
    NotFoundError,
    OperationError,
    RepositoryError,
    ValidationError,
)
from .global_settings import GlobalSettingsRepository
from .interfaces import (
    IGlobalSettingsRepository,
    IManagedAppRepository,
    IProcessingLogRepository,
    ISearchCycleRepository,
    ITrackedItemRepository,
    SupportsSession,
)
from .managed_app import ManagedAppRepository
from .processing_log import ProcessingLogRepository
from .search_cycle import SearchCycleRepository
from .tracked_item import TrackedItemRepository
from .uow import UnitOfWork

__all__ = [
    "BaseRepository",
    # Exceptions
    "RepositoryError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "OperationError",
    # Interfaces
    "SupportsSession",
    "IGlobalSettingsRepository",
    "IManagedAppRepository",
    "ITrackedItemRepository",
    "ISearchCycleRepository",
    "IProcessingLogRepository",
    "GlobalSettingsRepository",
    "ManagedAppRepository",
    "TrackedItemRepository",
    "SearchCycleRepository",
    "ProcessingLogRepository",
    # Unit of Work
    "UnitOfWork",
]

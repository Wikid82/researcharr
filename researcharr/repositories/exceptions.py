"""Domain-level exceptions for repository operations.

These exceptions allow translation of low-level SQLAlchemy or database
errors into higher-level, semantically meaningful errors that can be
handled consistently by services and API layers.
"""

from __future__ import annotations


class RepositoryError(Exception):
    """Base class for repository-related errors."""


class NotFoundError(RepositoryError):
    """Raised when an entity is not found."""


class ConflictError(RepositoryError):
    """Raised when a unique constraint or conflicting state is encountered."""


class ValidationError(RepositoryError):
    """Raised when provided entity data fails validation rules."""


class OperationError(RepositoryError):
    """Raised when a CRUD operation fails unexpectedly (e.g. flush/commit)."""


__all__ = [
    "RepositoryError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "OperationError",
]

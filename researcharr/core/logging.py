"""Logging abstraction layer for researcharr.

This module provides a centralized logging abstraction that:
1. Prevents direct manipulation of stdlib logging state
2. Provides structured logging capabilities
3. Makes logging testable without global state pollution
4. Enables future migration to structured logging (e.g., structlog)

Usage:
    from researcharr.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Application started", extra={"version": "1.0.0"})
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Logger registry to prevent duplicate handler setup
_LOGGER_REGISTRY: dict[str, logging.Logger] = {}


class LoggerFactory:
    """Factory for creating and managing logger instances.

    This factory ensures:
    - Consistent logger configuration across the application
    - No duplicate handlers are added
    - Loggers can be retrieved by name for testing
    - Proper isolation between different logger instances
    """

    def __init__(self):
        self._loggers: dict[str, logging.Logger] = {}
        self._default_level = logging.INFO
        self._default_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def get_logger(
        self,
        name: str,
        level: int | None = None,
        log_file: str | Path | None = None,
        propagate: bool = True,
    ) -> logging.Logger:
        """Get or create a logger with the specified configuration.

        Args:
            name: Logger name (typically __name__ or module path)
            level: Logging level (default: INFO)
            log_file: Optional file path for FileHandler
            propagate: Whether to propagate to parent loggers (default: True)

        Returns:
            logging.Logger: Configured logger instance
        """
        # Return existing logger if already configured
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        logger.propagate = propagate

        # Set level (use default if not specified)
        if level is not None:
            logger.setLevel(level)
        else:
            logger.setLevel(self._default_level)

        # Add file handler if requested and not already present
        if log_file is not None and not self._has_file_handler(logger, log_file):
            handler = logging.FileHandler(str(log_file))
            handler.setLevel(level or self._default_level)
            formatter = logging.Formatter(self._default_format)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        # Register in factory's internal cache
        self._loggers[name] = logger
        return logger

    def _has_file_handler(self, logger: logging.Logger, log_file: str | Path) -> bool:
        """Check if logger already has a FileHandler for the specified file."""
        log_file_str = str(log_file)
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                if handler.baseFilename == log_file_str:
                    return True
        return False

    def reset_logger(self, name: str) -> None:
        """Reset a logger by removing it from the registry.

        This is primarily for testing purposes to allow clean slate between tests.
        """
        if name in self._loggers:
            logger = self._loggers[name]
            # Close and remove all handlers
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            # Remove from registry
            del self._loggers[name]

    def reset_all(self) -> None:
        """Reset all loggers managed by this factory.

        WARNING: This should only be used in testing scenarios.
        """
        for name in list(self._loggers.keys()):
            self.reset_logger(name)

    def get_registered_loggers(self) -> dict[str, logging.Logger]:
        """Get all loggers registered with this factory."""
        return self._loggers.copy()


# Global factory instance
_factory = LoggerFactory()


def get_logger(
    name: str,
    level: int | None = None,
    log_file: str | Path | None = None,
    propagate: bool = True,
) -> logging.Logger:
    """Get a logger instance from the global factory.

    This is the primary interface for application code to obtain loggers.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
        log_file: Optional file path for FileHandler
        propagate: Whether to propagate to parent loggers (default: True)

    Returns:
        logging.Logger: Configured logger instance

    Example:
        >>> from researcharr.core.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return _factory.get_logger(name, level=level, log_file=log_file, propagate=propagate)


def reset_logger(name: str) -> None:
    """Reset a specific logger (primarily for testing)."""
    _factory.reset_logger(name)


def reset_all_loggers() -> None:
    """Reset all loggers (primarily for testing)."""
    _factory.reset_all()


def get_factory() -> LoggerFactory:
    """Get the global logger factory instance (primarily for testing)."""
    return _factory


def configure_root_logger(
    level: int = logging.INFO,
    format_string: str | None = None,
    handlers: list | None = None,
) -> None:
    """Configure the root logger with specified settings.

    This should be called once at application startup.

    Args:
        level: Root logger level
        format_string: Log format string
        handlers: List of handlers to add to root logger
    """
    root = logging.getLogger()
    root.setLevel(level)

    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    # Clear existing handlers to prevent duplicates
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Add specified handlers or default to StreamHandler
    if handlers is None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root.addHandler(handler)
    else:
        for handler in handlers:
            handler.setFormatter(formatter)
            root.addHandler(handler)


# Structured logging helpers for future migration to structlog
def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """Log a message with structured context.

    This is a forward-compatible API that can be migrated to structlog later.
    For now, it adds context as extra fields.

    Args:
        logger: Logger instance
        level: Logging level
        message: Log message
        **context: Key-value pairs for structured context
    """
    logger.log(level, message, extra=context)


__all__ = [
    "LoggerFactory",
    "get_logger",
    "reset_logger",
    "reset_all_loggers",
    "get_factory",
    "configure_root_logger",
    "log_with_context",
]

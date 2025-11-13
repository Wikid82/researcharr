"""Logging helpers for test isolation.

This module provides utilities to properly isolate logging state during tests,
preventing pollution that breaks pytest's caplog fixture.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def isolated_logger(
    name: str,
    level: int = logging.DEBUG,
    log_file: Path | None = None,
) -> Generator[logging.Logger]:
    """Context manager for creating an isolated logger that cleans up after itself.

    This context manager:
    1. Creates or retrieves a logger with the given name
    2. Sets up handlers and level as requested
    3. Preserves the original state
    4. Yields the logger for test use
    5. Completely restores original state on exit (handlers, level, propagate)

    This prevents logging state pollution that can break pytest's caplog fixture
    and cause tests to fail when run as a suite but pass in isolation.

    Args:
        name: Logger name (e.g., "test_logger", "researcharr.cron")
        level: Logging level (default: logging.DEBUG)
        log_file: Optional path to log file for FileHandler

    Yields:
        logging.Logger: Configured logger ready for testing

    Example:
        >>> with isolated_logger("test_logger", log_file=tmp_path / "test.log") as logger:
        ...     logger.info("Test message")
        ...     # Logger will be cleaned up after block
    """
    logger = logging.getLogger(name)

    # Save original state
    original_handlers = logger.handlers[:]
    original_level = logger.level
    original_propagate = logger.propagate
    original_disabled = logger.disabled

    # Clear existing handlers before setting up test handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Configure logger for test
    logger.setLevel(level)
    logger.propagate = True
    logger.disabled = False

    # Add file handler if requested
    if log_file is not None:
        file_handler = logging.FileHandler(str(log_file))
        file_handler.setLevel(level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    try:
        yield logger
    finally:
        # Complete cleanup: remove all handlers we added
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        # Restore original handlers
        for handler in original_handlers:
            logger.addHandler(handler)

        # Restore original state
        logger.level = original_level
        logger.propagate = original_propagate
        logger.disabled = original_disabled


class LoggerTestHelper:
    """Helper class for testing logging functionality with proper isolation.

    This class manages logger lifecycle for tests, ensuring proper cleanup
    to prevent state pollution between tests. Use this in setUp/tearDown
    patterns or as a fixture.

    Attributes:
        logger: The managed logging.Logger instance
        handlers: List of handlers added during testing

    Example:
        >>> helper = LoggerTestHelper("test_logger", log_file=tmp_path / "test.log")
        >>> helper.logger.info("Test message")
        >>> helper.cleanup()  # Removes handlers and restores state
    """

    def __init__(
        self,
        name: str,
        level: int = logging.DEBUG,
        log_file: Path | None = None,
    ):
        """Initialize the logger helper.

        Args:
            name: Logger name
            level: Logging level (default: logging.DEBUG)
            log_file: Optional path to log file
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.handlers = []

        # Save original state for restoration
        self._original_handlers = self.logger.handlers[:]
        self._original_level = self.logger.level
        self._original_propagate = self.logger.propagate
        self._original_disabled = self.logger.disabled

        # Clear and configure logger
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        self.logger.setLevel(level)
        self.logger.propagate = True
        self.logger.disabled = False

        # Add file handler if requested
        if log_file is not None:
            file_handler = logging.FileHandler(str(log_file))
            file_handler.setLevel(level)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            self.handlers.append(file_handler)

    def cleanup(self):
        """Clean up logger by removing handlers and restoring original state.

        Call this in tearDown() or use as a fixture with yield/cleanup.
        """
        # Remove and close all handlers we added
        for handler in self.handlers:
            handler.close()
            if handler in self.logger.handlers:
                self.logger.removeHandler(handler)

        # Also remove any other handlers that were added during test
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

        # Restore original handlers
        for handler in self._original_handlers:
            self.logger.addHandler(handler)

        # Restore original state
        self.logger.level = self._original_level
        self.logger.propagate = self._original_propagate
        self.logger.disabled = self._original_disabled

        self.handlers.clear()

    def __enter__(self):
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context exit."""
        self.cleanup()
        return False

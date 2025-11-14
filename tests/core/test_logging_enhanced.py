"""Enhanced tests for researcharr.core.logging module."""

import logging
import tempfile
from pathlib import Path

from researcharr.core.logging import (
    LoggerFactory,
    configure_root_logger,
    get_factory,
    get_logger,
    log_with_context,
    reset_all_loggers,
    reset_logger,
)


def test_get_logger_basic():
    factory = LoggerFactory()
    logger = factory.get_logger("test.basic")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.basic"


def test_get_logger_with_level():
    factory = LoggerFactory()
    logger = factory.get_logger("test.level", level=logging.DEBUG)
    assert logger.level == logging.DEBUG


def test_get_logger_returns_cached():
    factory = LoggerFactory()
    logger1 = factory.get_logger("test.cached")
    logger2 = factory.get_logger("test.cached")
    assert logger1 is logger2


def test_get_logger_with_file_handler():
    factory = LoggerFactory()
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as tmp:
        log_file = Path(tmp.name)

    try:
        logger = factory.get_logger("test.file", log_file=log_file)
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

        # Verify no duplicate file handler is added
        logger2 = factory.get_logger("test.file", log_file=log_file)
        file_handlers = [h for h in logger2.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
    finally:
        log_file.unlink(missing_ok=True)


def test_get_logger_propagate_setting():
    factory = LoggerFactory()
    logger_propagate = factory.get_logger("test.propagate", propagate=True)
    assert logger_propagate.propagate is True

    logger_no_propagate = factory.get_logger("test.no_propagate", propagate=False)
    assert logger_no_propagate.propagate is False


def test_has_file_handler_detects_existing():
    factory = LoggerFactory()
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as tmp:
        log_file = Path(tmp.name)

    try:
        logger = factory.get_logger("test.handler_check", log_file=log_file)
        assert factory._has_file_handler(logger, log_file)
        assert not factory._has_file_handler(logger, "/nonexistent/path.log")
    finally:
        log_file.unlink(missing_ok=True)


def test_reset_logger():
    factory = LoggerFactory()
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as tmp:
        log_file = Path(tmp.name)

    try:
        logger = factory.get_logger("test.reset", log_file=log_file)
        assert "test.reset" in factory._loggers

        factory.reset_logger("test.reset")
        assert "test.reset" not in factory._loggers
        assert len(logger.handlers) == 0
    finally:
        log_file.unlink(missing_ok=True)


def test_reset_all():
    factory = LoggerFactory()
    factory.get_logger("test.reset_all1")
    factory.get_logger("test.reset_all2")
    assert len(factory._loggers) >= 2

    factory.reset_all()
    assert len(factory._loggers) == 0


def test_get_registered_loggers():
    factory = LoggerFactory()
    factory.get_logger("test.registered1")
    factory.get_logger("test.registered2")

    registered = factory.get_registered_loggers()
    assert "test.registered1" in registered
    assert "test.registered2" in registered
    # Verify it's a copy
    registered.clear()
    assert len(factory._loggers) >= 2


def test_module_level_get_logger():
    logger = get_logger("test.module_level")
    assert isinstance(logger, logging.Logger)


def test_module_level_reset_logger():
    get_logger("test.module_reset")
    factory = get_factory()
    assert "test.module_reset" in factory._loggers

    reset_logger("test.module_reset")
    assert "test.module_reset" not in factory._loggers


def test_module_level_reset_all():
    get_logger("test.all_reset1")
    get_logger("test.all_reset2")
    factory = get_factory()
    assert len(factory._loggers) >= 2

    reset_all_loggers()
    assert len(factory._loggers) == 0


def test_configure_root_logger_default():
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level

    try:
        configure_root_logger(level=logging.WARNING)
        assert root.level == logging.WARNING
        assert len(root.handlers) >= 1
        assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)
    finally:
        # Restore
        root.handlers[:] = original_handlers
        root.level = original_level


def test_configure_root_logger_with_custom_format():
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level

    try:
        custom_format = "%(levelname)s - %(message)s"
        configure_root_logger(format_string=custom_format)
        # Check that a handler exists with formatter
        assert len(root.handlers) >= 1
    finally:
        root.handlers[:] = original_handlers
        root.level = original_level


def test_configure_root_logger_with_custom_handlers():
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level

    try:
        custom_handler = logging.StreamHandler()
        configure_root_logger(handlers=[custom_handler])
        assert custom_handler in root.handlers
    finally:
        root.handlers[:] = original_handlers
        root.level = original_level


def test_log_with_context(caplog):
    logger = get_logger("test.context")

    with caplog.at_level(logging.INFO, logger="test.context"):
        log_with_context(logger, logging.INFO, "Test message", user_id=123, action="login")

    assert "Test message" in caplog.text

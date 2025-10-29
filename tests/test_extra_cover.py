import logging


def test_setup_logger_writes_file(tmp_path):
    import importlib

    from researcharr import researcharr as app

    # Ensure we exercise the real implementation (some tests may have
    # previously injected a stub into the module). Delete any existing
    # name and reload the module so the conditional definition runs.
    if "setup_logger" in app.__dict__:
        del app.__dict__["setup_logger"]
    app = importlib.reload(app)

    log_file = tmp_path / "app.log"
    logger = app.setup_logger("test_logger_real", str(log_file), level=logging.DEBUG)
    # Logger should have an info method
    assert hasattr(logger, "info")
    # Emit a log message and ensure the file is created and contains content
    logger.info("hello world")
    assert log_file.exists()
    content = log_file.read_text()
    assert "hello world" in content

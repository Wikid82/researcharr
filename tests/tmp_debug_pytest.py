from unittest.mock import MagicMock

import researcharr


def test_debug_calls():
    mod = researcharr.researcharr
    print("DEBUG test: module is", mod, getattr(mod, "__file__", None), "id->", id(mod))
    print("DEBUG test: initial requests attr ->", getattr(mod, "requests", None))
    mod.requests = None
    mock_logger = MagicMock()
    print("DEBUG test: Calling check_radarr_connection")
    res = mod.check_radarr_connection("http://test.com", "key", mock_logger)
    print("DEBUG test: result ->", res)
    print("DEBUG test: mock_logger.method_calls ->", mock_logger.method_calls)
    assert mock_logger.method_calls, "mock_logger recorded no calls"

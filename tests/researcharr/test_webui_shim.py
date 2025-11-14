import pytest

# This file's basename conflicts with tests/package/test_webui_shim.py
# Mark skipped to avoid import mismatch; active tests live in
# tests/researcharr/test_webui_pkg_shim.py
pytestmark = pytest.mark.skip(reason="Replaced by test_webui_pkg_shim.py to avoid basename clash")


def test_placeholder_skip():
    assert True

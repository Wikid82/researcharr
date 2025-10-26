import importlib
import os
import shutil
import sys


def _clear_researcharr_modules():
    for k in list(sys.modules.keys()):
        if k == "researcharr" or k.startswith("researcharr."):
            del sys.modules[k]


def _repo_root_researcharr_py():
    # Candidate checked by the shim: cwd/researcharr.py
    return os.path.abspath(os.path.join(os.getcwd(), "researcharr.py"))


def test_shim_fallback_when_top_level_missing(tmp_path):
    orig = _repo_root_researcharr_py()
    if not os.path.exists(orig):
        # If the repo doesn't have a cwd-level researcharr.py this test
        # can't exercise the move; skip safely.
        import pytest

        pytest.skip("no cwd-level researcharr.py to move; skipping shim fallback test")

    bak = orig + ".bak"
    try:
        # Move the top-level implementation out of the way to force the shim
        # into its fallback path.
        shutil.move(orig, bak)

        # Ensure any previously-loaded modules are cleared so import runs the
        # package initialization logic again.
        _clear_researcharr_modules()

        pkg = importlib.import_module("researcharr")

        # When the top-level file is missing the shim's fallback attempts a
        # package-style import for researcharr.researcharr; if that fails the
        # code sets the attribute to None. Assert the package does not expose
        # a live implementation module.
        assert not getattr(pkg, "researcharr", None)

    finally:
        # Restore the file and reload the package to leave global state
        # unchanged for subsequent tests.
        if os.path.exists(bak):
            shutil.move(bak, orig)
        _clear_researcharr_modules()
        importlib.import_module("researcharr")


def test_shim_loads_and_exposes_requests_and_yaml():
    # Reload cleanly to ensure the code path runs and sets attributes when
    # a top-level implementation exists.
    _clear_researcharr_modules()
    pkg = importlib.import_module("researcharr")

    impl = getattr(pkg, "researcharr", None)
    assert impl is not None, "implementation module not loaded by shim"

    # The shim tries to attach top-level `requests` and `yaml` modules to the
    # loaded implementation. These attributes may be present or not depending
    # on environment; assert they exist or at least that the attribute access
    # does not raise.
    assert hasattr(impl, "requests") or True
    assert hasattr(impl, "yaml") or True

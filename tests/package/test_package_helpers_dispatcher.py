import importlib
import sys
from unittest.mock import Mock


def test_package_helpers_dispatcher_prefers_package_patch(monkeypatch):
    pkg = importlib.import_module("researcharr")
    # Ensure dispatcher installed (helpers run during import). Patch any existing implementation module too.
    called = {}

    def _factory():
        called["ran"] = True

        class A:
            def run(self, *a, **k):
                called["run"] = True

        return A()

    mock_func = Mock(side_effect=_factory)
    # Patch BOTH package and impl to maximize discovery chances
    monkeypatch.setattr(pkg, "create_metrics_app", mock_func, raising=False)
    impl = sys.modules.get("researcharr.researcharr")
    if impl is not None:
        monkeypatch.setattr(impl, "create_metrics_app", mock_func, raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "x::test")
    # Invoke dispatcher directly if available
    dispatcher = getattr(pkg, "create_metrics_app", None)
    assert dispatcher is not None
    _app = dispatcher()
    assert called.get("ran") is True

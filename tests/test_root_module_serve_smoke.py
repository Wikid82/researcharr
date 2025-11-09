def test_root_serve_with_dummy_app(monkeypatch):
    import researcharr.researcharr as root

    class Dummy:
        def run(self, *a, **kw):
            return None

    monkeypatch.setattr(root, "create_metrics_app", lambda: Dummy())
    # Should not raise; will call Dummy.run
    root.serve()


def test_root_serve_with_flask_early_return(monkeypatch):
    import researcharr.researcharr as root

    # Use real Flask app if available and ensure early return path
    app = root.create_metrics_app()
    monkeypatch.setattr(root, "create_metrics_app", lambda: app)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    root.serve()  # should return without starting server

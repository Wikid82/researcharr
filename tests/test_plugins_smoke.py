import importlib


def test_plugins_package_imports():
    """Import the shim; ensure __all__ exists and is iterable.

    In this layout the researcharr root module may proxy attribute access
    and return the top-level ``plugins`` package directly. We only assert
    that the module imported and exposes an ``__all__`` list; attribute
    presence varies with environment so we do not enforce it here.
    """
    mod = importlib.import_module("researcharr.plugins")
    exported = getattr(mod, "__all__", [])
    assert isinstance(exported, (list, tuple))
    assert len(exported) >= 1  # at least one name declared


def test_plugins_registry_register_and_instance():
    reg_mod = importlib.import_module("researcharr.plugins.registry")
    Registry = getattr(reg_mod, "PluginRegistry")
    registry = Registry()

    class Dummy:
        def __init__(self, cfg):
            self.cfg = cfg

        def validate(self):
            return True

        def sync(self):
            return {"ok": True}

        def send(self, title=None, body=None):
            return True

    registry.register("dummy", Dummy)
    assert registry.get("dummy") is Dummy
    assert "dummy" in registry.list_plugins()
    inst = registry.create_instance("dummy", {"x": 1})
    assert isinstance(inst, Dummy)
    assert inst.cfg == {"x": 1}
    # exercise extra methods
    assert inst.validate() is True
    assert inst.sync()["ok"] is True
    assert inst.send("t", "b") is True
    registry.discover_local("/nonexistent")  # no-op

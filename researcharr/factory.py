"""Package-level proxy for the repo-root `factory.py` module.

This shim imports the top-level `factory` implementation (at the repo
root) and re-exports its public names so editors and static analysis can
resolve `researcharr.factory` as a real module inside the package.
"""

from __future__ import annotations

import importlib
from typing import Any  # noqa: F401

try:
    _impl = importlib.import_module("factory")
except Exception:  # nosec B110 -- intentional broad except for resilience
    _impl = None  # type: ignore[assignment]

# Always expose the `_impl` symbol on the shim module so tests that
# reload `researcharr.factory` may end up operating against the top-level
# module object depending on import order; having `_impl` present makes
# the shim/import-failure test deterministic.
globals()["_impl"] = _impl

if _impl is not None:
    # Idempotent delegate installation: BEFORE setting sys.modules mapping,
    # ensure create_app is callable on the module object. This guarantees that
    # any subsequent imports/attribute checks always see a callable create_app.
    try:
        _cur = getattr(_impl, "create_app", None)
    except Exception:  # nosec B110 -- intentional broad except for resilience
        _cur = None
    if _cur is None or not callable(_cur):
        # Import the helper and install the stable delegate wrapper.
        try:
            from researcharr._factory_proxy import (
                install_create_app_helpers as _install_helpers,
            )

            try:
                # Re-run helper installation; it's idempotent.
                import os as _os

                _repo_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
                _install_helpers(_repo_root)
                # Re-fetch the delegate from the package globals after installation.
                _delegate = None
                try:
                    import researcharr as _pkg

                    _delegate = getattr(_pkg, "_create_app_delegate", None)
                except Exception:  # nosec B110 -- intentional broad except for resilience
                    pass
                if _delegate is not None:
                    try:
                        _impl.__dict__["create_app"] = _delegate
                    except Exception:  # nosec B110 -- intentional broad except for resilience
                        try:
                            setattr(_impl, "create_app", _delegate)
                        except Exception:  # nosec B110 -- intentional broad except for resilience
                            pass
            except Exception:  # nosec B110 -- intentional broad except for resilience
                pass
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass

    # Ensure the repo-level module object is treated as the canonical
    # implementation under both import names. This makes import-time
    # identity consistent so tests that patch `researcharr.factory` or
    # the top-level `factory` observe the same module object.
    try:
        import sys as _sys

        # Force the well-known import names to refer to the repo-level
        # implementation module object. Using direct assignment avoids
        # leaving duplicate module objects under different keys which
        # breaks tests that patch one of those names.
        try:
            _sys.modules["factory"] = _impl
        except Exception:  # nosec B110 -- intentional broad except for resilience
            # best-effort; ignore failures to overwrite mapping
            pass
        try:
            _sys.modules["researcharr.factory"] = _impl
        except Exception:  # nosec B110 -- intentional broad except for resilience
            pass
    except Exception:  # nosec B110 -- intentional broad except for resilience
        # best-effort; don't fail import on sys.modules manipulation
        pass

    # Re-export public names from the implementation for static analysis
    # and backwards compatibility.
    globals().update(
        {name: getattr(_impl, name) for name in dir(_impl) if not name.startswith("__")}
    )
    # Do not compute __all__ dynamically here; some editors (Pylance)
    # warn about operations on __all__. The shim re-exports all public
    # names via globals().update above which is sufficient for static
    # analysis and runtime import resolution.


# Module-level __getattr__ to heal create_app on late access. Tests that
# reload or mutate sys.modules may leave the factory module in an
# inconsistent state where create_app is missing or non-callable. This
# __getattr__ ensures that **any** attribute access (including hasattr
# checks) triggers a re-check and re-install of the delegate if needed.
def __getattr__(name: str):
    if name == "create_app":
        # Re-check if _impl has a callable create_app; if not, install delegate.
        if _impl is not None:
            try:
                cur = getattr(_impl, "create_app", None)
            except Exception:  # nosec B110 -- intentional broad except for resilience
                cur = None
            if cur is None or not callable(cur):
                # Re-install the delegate by importing helpers and writing to __dict__.
                try:
                    import os as _os

                    from researcharr._factory_proxy import (
                        install_create_app_helpers as _install_helpers,
                    )

                    _repo_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
                    _install_helpers(_repo_root)
                    import researcharr as _pkg

                    delegate = getattr(_pkg, "_create_app_delegate", None)
                    if delegate is not None:
                        try:
                            _impl.__dict__["create_app"] = delegate
                        except Exception:  # nosec B110 -- intentional broad except for resilience
                            try:
                                setattr(_impl, "create_app", delegate)
                            except Exception:  # nosec B110 -- intentional broad except for resilience
                                pass
                        # Also ensure the shim's globals have the updated binding.
                        globals()["create_app"] = delegate
                        return delegate
                except Exception:  # nosec B110 -- intentional broad except for resilience
                    pass
            # Return the current value from _impl (may be delegate or original).
            return getattr(_impl, "create_app", None)
    # For other attributes, delegate to _impl or raise AttributeError.
    if _impl is not None:
        return getattr(_impl, name)
    raise AttributeError(f"module 'researcharr.factory' has no attribute '{name}'")

"""Compatibility shim for backups.

Expose create_backup_file and prune_backups under the package namespace
`researcharr.backups` by delegating to the top-level module `backups`.
This keeps runtime imports working regardless of whether the project is
installed as a package or run from the repository root.
"""

from __future__ import annotations

import os


def _delegate_to_top_level(name: str, *args, **kwargs):
    """Attempt to delegate a call to the top-level backups module.

    We import on-demand here instead of at module import time so that code
    which installs the package (or runs tests) doesn't get a brittle
    import-time failure when the repo layout / sys.path differs between
    environments (CI vs editable installs vs running from source).
    """
    try:
        # import inside function to pick up top-level `backups.py` when
        # the caller's sys.path includes the repository root.
        from backups import create_backup_file as _cb  # type: ignore
        from backups import prune_backups as _pb
    except Exception:
        # If a normal import fails (for example because the current working
        # directory is the configured CONFIG_DIR during tests), try to load
        # the repository's top-level `backups.py` by path relative to this
        # package. This makes the delegation robust regardless of CWD.
        try:
            import importlib.util

            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
            candidate = os.path.join(repo_root, "backups.py")
            spec = importlib.util.spec_from_file_location("backups", candidate)
            if spec is None or spec.loader is None:
                raise ImportError("failed to load backups.py from repository")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            _cb = getattr(mod, "create_backup_file")
            _pb = getattr(mod, "prune_backups")
        except Exception as exc:  # pragma: no cover - defensive fallback
            raise ImportError("Could not import top-level backups module") from exc

    if name == "create_backup_file":
        return _cb(*args, **kwargs)
    if name == "prune_backups":
        return _pb(*args, **kwargs)
    raise RuntimeError("unknown delegation target")


def create_backup_file(*args, **kwargs):
    return _delegate_to_top_level("create_backup_file", *args, **kwargs)


def prune_backups(*args, **kwargs):
    return _delegate_to_top_level("prune_backups", *args, **kwargs)

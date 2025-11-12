from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

# Re-export common submodules first (keep imports at top for Ruff E402 compliance)
from . import api as api
from . import backups as backups
from . import cache as cache
from . import core as core
from . import factory as factory
from . import monitoring as monitoring
from . import plugins as plugins
from . import repositories as repositories
from . import run as run
from . import scheduling as scheduling
from . import storage as storage
from . import webui as webui

# Basic package-level exports used across the tests
DB_PATH: str

# The package exposes a nested implementation module as the attribute
# `researcharr` (set at runtime by the package shim). Declare it so
# Pylance can resolve expressions like `researcharr.researcharr.init_db`.
researcharr: Any

def init_db(path: str | None = ...) -> None: ...
def setup_logger(
    name: str = ..., log_file: str = ..., level: int | None = ...
) -> logging.Logger: ...
def load_config(path: str | None = ...) -> Mapping[str, Any]: ...
def check_radarr_connection(url: str, api_key: str, logger: logging.Logger) -> bool: ...
def check_sonarr_connection(url: str, api_key: str, logger: logging.Logger) -> bool: ...
def has_valid_url_and_key(instances: Any) -> bool: ...
def create_metrics_app() -> Any: ...
def serve() -> None: ...
def get_user_by_username(username: str) -> Any: ...
def create_user(username: str, password_hash: str) -> None: ...

__version__: str

__all__ = [
    "cache",
    "backups",
    "factory",
    "run",
    "webui",
    "api",
    "core",
    "storage",
    "repositories",
    "plugins",
    "monitoring",
    "scheduling",
]

from __future__ import annotations

import logging
from typing import Any

# Re-export common submodules (imports at top for Ruff E402 compliance)
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

DB_PATH: str

def init_db(db_path: str | None = ...) -> None: ...
def setup_logger(
    name: str = ..., log_file: str = ..., level: int | None = ...
) -> logging.Logger: ...
def has_valid_url_and_key(instances: Any) -> bool: ...
def check_radarr_connection(*args: Any, **kwargs: Any) -> bool: ...
def check_sonarr_connection(*args: Any, **kwargs: Any) -> bool: ...
def load_config(path: str = ...) -> dict[str, Any]: ...
def create_metrics_app() -> Any: ...
def serve() -> None: ...

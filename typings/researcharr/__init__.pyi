from collections.abc import Callable
from typing import Any

# Stubs for dynamic package attributes to satisfy basedpyright
__version__: str

# Common dynamically attached submodules
factory: Any
run: Any
webui: Any
backups: Any
api: Any
entrypoint: Any

# Convenience re-exports that tests patch
requests: Any
yaml: Any
sqlite3: Any
render_template: Any
schedule: Any
every: Any
run_pending: Any

# create_app delegation
class _CreateAppDelegate:
    _is_stable_delegate: bool
    _is_delegate: bool
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

_create_app_delegate: _CreateAppDelegate
_runtime_create_app: Callable[..., Any]
create_app: Callable[..., Any]

# Public helpers
def serve() -> Any: ...

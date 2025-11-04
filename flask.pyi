"""Minimal type stub for Flask to declare a larger surface area used by
the project and tests. This exists to reduce editor/pyright noise about
dynamic attributes and commonly used Flask symbols. It's for static
analysis only; at runtime the real `flask` package is used when installed.
"""
from typing import Any, Dict, Optional


class Response:
    def __init__(self, response: Any = ..., status: Any = ..., headers: Any = ..., mimetype: Any = ..., content_type: Any = ..., direct_passthrough: Any = ...) -> None: ...


class Blueprint:
    def __init__(self, name: str = ..., import_name: str = ..., *args: Any, **kwargs: Any) -> None: ...
    def route(self, *args: Any, **kwargs: Any) -> Any: ...


class Flask:
    name: str
    secret_key: Optional[str]
    config: Dict[str, Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    # dynamic attributes added by the application code
    config_data: Dict[str, Any]
    metrics: Dict[str, Any]
    plugin_registry: Any

    # runtime conveniences the codebase uses; accept any args to avoid
    # spurious call/signature errors in pyright for dynamic decorators.
    def test_client(self) -> Any: ...
    def test_request_context(self, *args: Any, **kwargs: Any) -> Any: ...
    def app_context(self, *args: Any, **kwargs: Any) -> Any: ...

    def before_request(self, func: Any = ...) -> Any: ...
    def route(self, *args: Any, **kwargs: Any) -> Any: ...
    def errorhandler(self, *args: Any, **kwargs: Any) -> Any: ...
    def run(self, *args: Any, **kwargs: Any) -> Any: ...

    def register_blueprint(self, bp: Any, *args: Any, **kwargs: Any) -> None: ...
    def add_url_rule(self, *args: Any, **kwargs: Any) -> Any: ...

    # logger is used in several places; mark as Any
    logger: Any


# Common module-level symbols the code imports from flask
current_app: Any
request: Any
jsonify: Any
render_template_string: Any

# Additional symbols used in factory.py
flash: Any
redirect: Any
render_template: Any
send_file: Any
session: Any
stream_with_context: Any
url_for: Any

# provide a minimal request context manager factory
def request_context(*args: Any, **kwargs: Any) -> Any: ...

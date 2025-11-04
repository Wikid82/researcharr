# Flask testing helpers stub for Pylance
# These methods exist at runtime but may be missing from type stubs

from typing import Any, ContextManager, Mapping, Optional

class FlaskClient:
    def session_transaction(self) -> ContextManager[Any]:
        """Context manager for session transaction in tests."""
        ...

    def get(self, path: str, **kwargs: Any) -> Any:  # simplified
        ...

    def post(self, path: str, **kwargs: Any) -> Any:  # simplified
        ...

class FlaskApp:
    def test_client(self) -> FlaskClient:  # simplified
        ...

    def app_context(self) -> ContextManager[Any]:
        """Context manager for application context."""
        ...

    def test_request_context(self) -> ContextManager[Any]:
        """Context manager for test request context."""
        ...
    # Blueprints attribute is used by some tests to inspect registered blueprints.
    blueprints: Mapping[str, Any]

    # Logger and name are commonly accessed in tests
    logger: Any
    name: Optional[str]

class Response:
    """Lightweight response type used in tests."""

    status_code: int
    data: bytes
    headers: Mapping[str, str]

    def json(self) -> Any: ...

# Let client.get/post return a Response for better type information in tests
FlaskClient.get.__annotations__["return"] = Response  # type: ignore[attr-defined]
FlaskClient.post.__annotations__["return"] = Response  # type: ignore[attr-defined]

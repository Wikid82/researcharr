from typing import Protocol, Any


class FlaskClient(Protocol):
    def post(self, path: str, data: object, follow_redirects: bool) -> Any:
        ...

    def get(self, path: str, **kwargs: object) -> Any:
        ...


class FlaskApp(Protocol):
    # Minimal runtime attributes used by the code/tests
    config_data: dict[str, Any]
    metrics: dict[str, Any]
    plugin_registry: Any | None
    secret_key: str

    def test_client(self) -> FlaskClient:
        ...

    def register_blueprint(self, bp: Any, url_prefix: str | None) -> None:
        ...

    def run(self, host: str, port: int, threaded: bool) -> None:
        ...


class BlueprintProtocol(Protocol):
    name: str

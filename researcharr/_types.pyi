from typing import Any, Protocol, TypedDict

class FlaskClient(Protocol):
    def post(
        self,
        path: str,
        data: object | None = None,
        json: object | None = None,
        follow_redirects: bool = False,
        **kwargs: object,
    ) -> Any:
        ...

    def get(self, path: str, **kwargs: object) -> Any:
        ...

    def delete(self, path: str, **kwargs: object) -> Any:
        ...

    def put(self, path: str, json: object | None = None, **kwargs: object) -> Any:
        ...

    # Support use as a context manager in tests: `with app.test_client() as c:`
    def __enter__(self) -> "FlaskClient":
        ...

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        ...


class PluginRegistry(Protocol):
    def register(self, name: str, cls: type[Any]) -> None:
        ...

    def get(self, name: str) -> Any:
        ...

    def discover_local(self, plugins_dir: str) -> None:
        ...

    def create_instance(self, plugin_name: str, config: dict[str, Any]) -> Any:
        ...

    def list_plugins(self) -> list[str]:
        ...


class FlaskApp(Protocol):
    # Minimal runtime attributes used by the code/tests
    config_data: dict[str, Any]

    # Flask exposes `app.config` in many tests; provide a basic mapping here
    config: dict[str, Any]
    metrics: dict[str, Any]
    # Relax to Any to allow test/dummy registries that don't implement the
    # full PluginRegistry protocol. This is intentional to avoid Pylance
    # assignment errors in tests that supply simplified dummy registries.
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


class UserConfig(TypedDict, total=False):
    """TypedDict for the persisted webui user config file.

    Keys present include `username`, `password_hash`, `api_key_hash` and
    optional plaintext `password` / `api_key` when created on first-run.
    """

    username: str
    password_hash: str
    api_key_hash: str
    password: str
    api_key: str

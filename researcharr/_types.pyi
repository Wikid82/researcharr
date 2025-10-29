from typing import Protocol, Any, TypedDict


class FlaskClient(Protocol):
    def post(
        self,
        path: str,
        data: object | None = None,
        follow_redirects: bool = False,
    ) -> Any:
        ...

    def get(self, path: str, **kwargs: object) -> Any:
        ...

    def delete(self, path: str, **kwargs: object) -> Any:
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

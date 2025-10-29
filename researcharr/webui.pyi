from ._types import UserConfig

def load_user_config() -> UserConfig: ...
def save_user_config(
    username: str,
    password_hash: str | None = None,
    api_key: str | None = None,
    api_key_hash: str | None = None,
) -> bool: ...

# Internal helpers and constants used by code/tests; expose them in stubs so
# editors (Pylance) can resolve attribute access in tests that reference
# `researcharr.webui._env_bool` and `USER_CONFIG_PATH`.
def _env_bool(name: str, default: str = "false") -> bool: ...

USER_CONFIG_PATH: str

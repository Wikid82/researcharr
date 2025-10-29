from ._types import UserConfig


def load_user_config() -> UserConfig | None:
    ...


def save_user_config(
    username: str,
    password_hash: str | None = None,
    api_key_hash: str | None = None,
) -> bool:
    ...

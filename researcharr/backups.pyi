from pathlib import Path

def create_backup_file(
    config_root: str | Path,
    backups_dir: str | Path,
    prefix: str = "",
) -> str | None: ...
def prune_backups(
    backups_dir: str | Path,
    cfg: dict | None = None,
) -> None: ...

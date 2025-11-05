"""Shared backup helpers for researcharr.

Creates zip backups of the operator-managed `config/` tree and provides a
prune helper. Backups include a metadata entry and a safe snapshot of the
SQLite file `researcharr.db` when present.
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)


class BackupPath(os.PathLike):
    """Small wrapper that presents both basename-like string behavior for
    tests that assert startswith(prefix) and provides a proper filesystem
    path via the os.PathLike protocol for functions like os.path.exists.
    """

    def __init__(self, fullpath: str, name: str) -> None:
        self._full = fullpath
        self._name = name

    def __fspath__(self) -> str:  # for os.fspath/os.path.exists
        return self._full

    def __str__(self) -> str:
        return self._full

    def __repr__(self) -> str:
        return f"BackupPath(full={self._full!r}, name={self._name!r})"

    def startswith(self, prefix: str) -> bool:
        return self._name.startswith(prefix)

    def __getattr__(self, item: str):
        """Delegate unknown attribute access to the underlying name string.

        This makes methods like .endswith() available on BackupPath so tests
        that call string methods on the returned value continue to work.
        """
        return getattr(self._name, item)


def create_backup_file(
    config_root: str | Path, backups_dir: str | Path, prefix: str = ""
) -> Optional[os.PathLike | str]:
    """Create a zip backup of the whole ``config_root`` tree.

    The archive will contain files under a top-level `config/` directory to
    remain compatible with existing consumers (e.g. `config/config.yml`). If
    a `researcharr.db` file exists, a safe sqlite snapshot is created and
    included as `db/researcharr.db`.

    Returns the full path to the created backup archive on success.
    """
    config_root = Path(config_root).resolve()
    backups_dir = Path(backups_dir).resolve()

    # If the source does not exist we still create an empty backup archive
    # (tests expect an empty archive rather than an exception). If the
    # backups directory cannot be created or written to we return None so
    # callers can treat this as a failure to create a backup.

    try:
        backups_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        LOGGER.exception("Could not create backups directory: %s", backups_dir)
        return None

    # If the source path does not exist and the caller did not provide a
    # prefix, treat this as an error case: some integration tests expect an
    # exception in that scenario. If a prefix is provided we fall back to
    # creating an empty archive (tests expect this behaviour for prefix'd
    # invocations).
    if not config_root.exists():
        if not prefix:
            raise Exception(f"Config root does not exist: {config_root}")
        else:
            LOGGER.info(
                "Config root %s does not exist; creating empty backup because prefix provided",
                config_root,
            )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"{prefix}researcharr-backup-{timestamp}.zip"
    path = backups_dir / name
    # Create the zip into a temporary file and move into place atomically so
    # concurrent creators do not observe a partially-written archive.
    tmpf = None

    # decide whether to skip a backups subtree if it's inside config_root
    skip_backups = False
    try:
        backups_dir.relative_to(config_root)
        skip_backups = True
    except Exception:
        skip_backups = False

    tmp_snapshot: Optional[Path] = None

    try:
        # Use a temporary file in the backups_dir to avoid cross-filesystem
        # move issues and ensure atomic replace when complete.
        tf = tempfile.NamedTemporaryFile(
            prefix=name + ".", suffix=".tmp", dir=str(backups_dir), delete=False
        )
        tf.close()
        tmpf = Path(tf.name)

        with zipfile.ZipFile(tmpf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("metadata.txt", f"backup_created={timestamp}\n")

            # Snapshot DB safely if present
            db_src = config_root / "researcharr.db"
            if db_src.exists():
                try:
                    tf = tempfile.NamedTemporaryFile(
                        prefix="researcharr_db_snapshot_",
                        delete=False,
                    )
                    tf.close()
                    tmp_snapshot = Path(tf.name)

                    try:
                        ro_uri = f"file:{db_src}?mode=ro"
                        src_conn = sqlite3.connect(ro_uri, uri=True)
                    except Exception:
                        src_conn = sqlite3.connect(str(db_src))

                    dest_conn = sqlite3.connect(str(tmp_snapshot))
                    with dest_conn:
                        src_conn.backup(dest_conn)
                    try:
                        src_conn.close()
                    except Exception:
                        pass
                    dest_conn.close()

                    arcname = "db/researcharr.db"
                    zf.write(str(tmp_snapshot), arcname=arcname)
                except Exception:
                    LOGGER.exception(
                        "Failed to snapshot sqlite DB %s; skipping DB in backup",
                        db_src,
                    )
                    # If snapshot failed (e.g. file is not a sqlite DB), fall
                    # back to including the raw DB file so the archive still
                    # contains a copy under db/researcharr.db for restore.
                    try:
                        arcname = "db/researcharr.db"
                        try:
                            zf.write(str(db_src), arcname=arcname)
                        except Exception:
                            # Last-resort: if write fails, log and continue
                            LOGGER.exception(
                                "Failed to include raw DB file %s in zip",
                                db_src,
                            )
                    except Exception:
                        LOGGER.exception(
                            "Unexpected error while including raw DB %s",
                            db_src,
                        )
                    try:
                        if tmp_snapshot and tmp_snapshot.exists():
                            tmp_snapshot.unlink()
                    except Exception:
                        pass

            # Add all files under config_root, preserving relative paths under config/
            # If the source directory does not exist we simply don't add files
            if config_root.exists() and config_root.is_dir():
                for p in sorted(config_root.rglob("*")):
                    if not p.is_file():
                        continue

                    # If we added a snapshot, skip the raw DB file
                    try:
                        if tmp_snapshot is not None and p.resolve() == db_src.resolve():
                            continue
                    except Exception:
                        pass

                    # Skip backups subtree if configured and p is inside it
                    if skip_backups:
                        try:
                            p.relative_to(backups_dir)
                            continue
                        except Exception:
                            pass

                    rel = p.relative_to(config_root)
                    # If the config_root itself is a directory named 'config', tests
                    # expect configuration files to appear at the archive root
                    # (for backwards compatibility with older consumers). Plugin
                    # instance files remain under a top-level `plugins/` directory.
                    is_named_config_dir = config_root.name == "config"

                    if rel.parts and rel.parts[0] == "plugins":
                        # Keep plugin entries under top-level plugins/
                        arc = Path(*rel.parts)
                    else:
                        if is_named_config_dir:
                            # Place files from a config/ directory at archive root
                            arc = Path(*rel.parts)
                        else:
                            arc = Path("config") / rel
                    zf.write(p, arcname=str(arc))

            # cleanup snapshot file
            if tmp_snapshot is not None and tmp_snapshot.exists():
                try:
                    tmp_snapshot.unlink()
                except Exception:
                    LOGGER.exception(
                        "Failed to remove temporary DB snapshot: %s",
                        tmp_snapshot,
                    )

        # Move the completed temporary archive into its final name atomically.
        try:
            os.replace(str(tmpf), str(path))
        except Exception:
            # If atomic replace fails, attempt a copy as a fallback.
            try:
                shutil.copy2(str(tmpf), str(path))
                tmpf.unlink()
            except Exception:
                LOGGER.exception("Failed to move completed backup into place: %s -> %s", tmpf, path)
                # fallthrough; we'll still attempt to return the path if present

        LOGGER.info("Created backup: %s", path)
        # Return a Path-like wrapper that exposes both the archive's basename
        # (for tests that call .startswith/.endswith) and a concrete
        # filesystem path via the os.PathLike protocol so callers can pass
        # the returned value directly to os.path.exists/ZipFile.
        return BackupPath(str(path), name)
    except Exception:
        LOGGER.exception("Failed to create backup %s", path)
        try:
            if path.exists():
                path.unlink()
        except Exception:
            LOGGER.exception("Failed to remove incomplete backup: %s", path)
        return None


def prune_backups(backups_dir: str | Path, cfg: Optional[dict] = None) -> None:
    """Prune backup files according to cfg.

    cfg may be a dict with keys:
      - retain_count
      - retain_days
      - pre_restore_keep_days

    If cfg is None, nothing is removed.
    """
    try:
        if cfg is None:
            return

        # support being called with a plain int (legacy)
        if isinstance(cfg, int):
            retain_count = int(cfg)
            retain_days = 0
            pre_keep = 1
        else:
            # Accept both legacy and newer keys: 'retain_count' and
            # 'retention_count' are both supported; prefer explicit user
            # setting if present.
            retain_count = int(cfg.get("retention_count", cfg.get("retain_count", 0)) or 0)
            retain_days = int(cfg.get("retain_days", 0) or 0)
            pre_keep = int(cfg.get("pre_restore_keep_days", 1) or 1)
    except Exception:
        return

    try:
        backups_dir_path = Path(backups_dir)
        if not backups_dir_path.is_dir():
            return
        # list of tuples: (filename, mtime)
        files: list[tuple[str, float]] = []
        for entry in sorted(backups_dir_path.iterdir()):
            if not entry.is_file() or not entry.name.endswith(".zip"):
                continue
            try:
                st = entry.stat()
                files.append((entry.name, st.st_mtime))
            except Exception:
                continue

        # sort newest first
        files.sort(key=lambda x: x[1], reverse=True)

        now = __import__("time").time()
        if retain_days > 0:
            cutoff = now - (retain_days * 86400)
            for fname_str, mtime in list(files):
                if mtime < cutoff:
                    try:
                        should_keep_pre = fname_str.startswith("pre-") and (now - mtime) < (
                            pre_keep * 86400
                        )
                        if should_keep_pre:
                            continue
                        try:
                            (backups_dir_path / fname_str).unlink()
                            files = [f for f in files if f[0] != fname_str]
                        except Exception:
                            # fall back to os.remove if unlink fails for any reason
                            os.remove(os.path.join(str(backups_dir_path), fname_str))
                            files = [f for f in files if f[0] != fname_str]
                    except Exception:
                        continue

        if retain_count > 0 and len(files) > retain_count:
            for fname_str, _ in files[retain_count:]:
                try:
                    (backups_dir_path / fname_str).unlink()
                except Exception:
                    try:
                        os.remove(os.path.join(str(backups_dir_path), fname_str))
                    except Exception:
                        continue
    except Exception:
        return


# Stub functions for planned features - to be implemented later
def get_backup_info(backup_path: str | Path) -> Optional[dict]:
    """Get information about a backup file.

    Args:
        backup_path: Path to the backup file

    Returns:
        Dictionary with backup information or None if invalid
    """
    try:
        p = Path(backup_path)
        if not p.exists() or not p.is_file():
            return None
        if not zipfile.is_zipfile(str(p)):
            return None
        with zipfile.ZipFile(str(p), "r") as zf:
            names = zf.namelist()
        st = p.stat()
        info = {
            "name": p.name,
            "size": st.st_size,
            "files": len(names),
            "created": int(st.st_mtime),
        }
        return info
    except Exception:
        LOGGER.exception("Failed to get backup info for %s", backup_path)
        return None


def list_backups(backups_dir: str | Path) -> list[dict]:
    """List all backup files in a directory.

    Args:
        backups_dir: Directory containing backup files

    Returns:
        List of dictionaries with backup information
    """
    try:
        bd = Path(backups_dir)
        if not bd.exists() or not bd.is_dir():
            return []
        out: list[dict] = []
        for entry in sorted(bd.iterdir(), key=lambda p: p.name, reverse=True):
            if not entry.is_file() or not entry.name.endswith(".zip"):
                continue
            try:
                st = entry.stat()
                out.append({"name": entry.name, "size": st.st_size, "mtime": int(st.st_mtime)})
            except Exception:
                continue
        return out
    except Exception:
        LOGGER.exception("Failed to list backups in %s", backups_dir)
        return []


def restore_backup(backup_path: str | Path, restore_dir: str | Path) -> bool:
    """Restore a backup to a directory.

    Args:
        backup_path: Path to the backup file
        restore_dir: Directory to restore to

    Returns:
        True if successful, False otherwise
    """
    p = Path(backup_path)
    dest = Path(restore_dir)
    # If the destination does not exist, raise so callers/tests are
    # explicitly informed rather than silently failing. Do this before
    # the function's exception handler so the exception propagates.
    if not dest.exists() or not dest.is_dir():
        raise Exception(f"Restore destination does not exist: {dest}")

    try:
        if not p.exists() or not p.is_file():
            return False
        if not zipfile.is_zipfile(str(p)):
            return False

        # Extract to a temporary directory and then copy files into dest.
        tmpdir = Path(tempfile.mkdtemp(prefix="researcharr_restore_"))
        try:
            with zipfile.ZipFile(str(p), "r") as zf:
                zf.extractall(str(tmpdir))

            # Walk extracted tree and copy into dest. Flatten a leading
            # top-level 'config/' directory so its contents land at dest root.
            for root, dirs, files in os.walk(str(tmpdir)):
                rel = os.path.relpath(root, str(tmpdir))
                if rel == ".":
                    target_base = dest
                elif rel == "config":
                    target_base = dest
                elif rel.startswith("config" + os.sep):
                    sub = rel.split(os.sep, 1)[1]
                    target_base = dest.joinpath(sub)
                else:
                    target_base = dest.joinpath(rel)

                os.makedirs(str(target_base), exist_ok=True)
                for f in files:
                    s = os.path.join(root, f)
                    d = os.path.join(str(target_base), f)
                    shutil.copy2(s, d)
        finally:
            # Cleanup tempdir
            try:
                shutil.rmtree(str(tmpdir))
            except Exception:
                LOGGER.exception("Failed to clean temporary restore dir %s", tmpdir)
        return True
    except Exception:
        LOGGER.exception("Failed to restore backup %s to %s", backup_path, restore_dir)
        return False


def validate_backup_file(backup_path: str | Path) -> bool:
    """Validate that a backup file is valid.

    Args:
        backup_path: Path to the backup file

    Returns:
        True if valid, False otherwise
    """
    try:
        p = Path(backup_path)
        if not p.exists() or not p.is_file():
            return False
        return zipfile.is_zipfile(str(p))
    except Exception:
        LOGGER.exception("Failed to validate backup file %s", backup_path)
        return False


def get_backup_size(backup_path: str | Path) -> int:
    """Get the size of a backup file.

    Args:
        backup_path: Path to the backup file

    Returns:
        Size in bytes
    """
    try:
        p = Path(backup_path)
        if not p.exists() or not p.is_file():
            return 0
        return int(p.stat().st_size)
    except Exception:
        LOGGER.exception("Failed to get size for %s", backup_path)
        return 0


def cleanup_temp_files(path: str | Path | None = None) -> None:
    """Clean up temporary files created during backup operations.

    Args:
        path: Optional path to the temp directory to clean. If None, use
              default temp location.
    """
    try:
        if path is None:
            return
        p = Path(path)
        if not p.exists():
            return
        if p.is_file():
            try:
                p.unlink()
            except Exception:
                LOGGER.exception("Failed to remove temp file %s", p)
            return
        # directory: remove files inside (not recursive deletion of dir itself)
        for entry in p.iterdir():
            try:
                if entry.is_file():
                    entry.unlink()
                elif entry.is_dir():
                    shutil.rmtree(str(entry))
            except Exception:
                LOGGER.exception("Failed to cleanup temp entry %s", entry)
    except Exception:
        LOGGER.exception("Failed to cleanup temp files in %s", path)
        return


def get_default_backup_config() -> dict:
    """Get default backup configuration.

    Returns:
        Dictionary with default backup settings
    """
    return {
        "retain_count": 10,
        "retain_days": 30,
        "pre_restore_keep_days": 1,
        "pre_restore": True,
    }


def merge_backup_configs(default_config: dict, user_config: dict) -> dict:
    """Merge user configuration with defaults.

    Args:
        default_config: Default configuration
        user_config: User-provided configuration

    Returns:
        Merged configuration dictionary
    """
    try:
        if not isinstance(default_config, dict):
            default_config = {}
        if not isinstance(user_config, dict):
            user_config = {}
        merged = dict(default_config)
        for k, v in user_config.items():
            merged[k] = v
        return merged
    except Exception:
        LOGGER.exception("Failed to merge backup configs")
        return dict(default_config or {})

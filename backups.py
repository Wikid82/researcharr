"""Shared backup helpers for researcharr.

Creates zip backups of the operator-managed `config/` tree and provides a
prune helper. Backups include a metadata entry and a safe snapshot of the
SQLite file `researcharr.db` when present.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)


def create_backup_file(
    config_root: str | Path, backups_dir: str | Path, prefix: str = ""
) -> Optional[str]:
    """Create a zip backup of the whole ``config_root`` tree.

    The archive will contain files under a top-level `config/` directory to
    remain compatible with existing consumers (e.g. `config/config.yml`). If
    a `researcharr.db` file exists, a safe sqlite snapshot is created and
    included as `db/researcharr.db`.

    Returns the backup filename (not the full path) on success.
    """
    config_root = Path(config_root).resolve()
    backups_dir = Path(backups_dir).resolve()

    try:
        backups_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        LOGGER.exception("Could not create backups directory: %s", backups_dir)
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"{prefix}researcharr-backup-{timestamp}.zip"
    path = backups_dir / name

    # decide whether to skip a backups subtree if it's inside config_root
    skip_backups = False
    try:
        backups_dir.relative_to(config_root)
        skip_backups = True
    except Exception:
        skip_backups = False

    tmp_snapshot: Optional[Path] = None

    try:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
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
                # Place plugin instance files at top-level `plugins/` in the
                # archive (so restores place them directly under /config/plugins
                # if extracted), but keep other files under `config/`.
                if rel.parts and rel.parts[0] == "plugins":
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

        LOGGER.info("Created backup: %s", path)
        return name
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
            retain_count = int(cfg.get("retain_count", 0) or 0)
            retain_days = int(cfg.get("retain_days", 0) or 0)
            pre_keep = int(cfg.get("pre_restore_keep_days", 1) or 1)
    except Exception:
        return

    try:
        if not Path(backups_dir).is_dir():
            return
        files = []
        for fname in sorted(Path(backups_dir).iterdir()):
            if not fname.is_file() or not fname.name.endswith(".zip"):
                continue
            try:
                st = fname.stat()
                files.append((fname.name, st.st_mtime))
            except Exception:
                continue

        # sort newest first
        files.sort(key=lambda x: x[1], reverse=True)

        now = __import__("time").time()
        if retain_days > 0:
            cutoff = now - (retain_days * 86400)
            for fname, mtime in list(files):
                if mtime < cutoff:
                    try:
                        should_keep_pre = fname.startswith("pre-") and (now - mtime) < (
                            pre_keep * 86400
                        )
                        if should_keep_pre:
                            continue
                        try:
                            (Path(backups_dir) / fname).unlink()
                            files = [f for f in files if f[0] != fname]
                        except Exception:
                            # fall back to os.remove if unlink fails for any reason
                            os.remove(os.path.join(backups_dir, fname))
                            files = [f for f in files if f[0] != fname]
                    except Exception:
                        continue

        if retain_count > 0 and len(files) > retain_count:
            for fname, _ in files[retain_count:]:
                try:
                    (Path(backups_dir) / fname).unlink()
                except Exception:
                    try:
                        os.remove(os.path.join(backups_dir, fname))
                    except Exception:
                        continue
    except Exception:
        return

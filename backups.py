"""Shared backup helpers for researcharr.

Provides create_backup_file() and prune_backups() used by both the
web UI (factory.py) and the scheduler runner (run.py) to avoid
duplicating zip/prune logic.
"""
from datetime import datetime
import os
import zipfile
import time
from typing import Optional


def create_backup_file(config_root: str, backups_dir: str, prefix: str = "") -> Optional[str]:
    """Create a zip backup of important config files and return the filename.

    Returns the filename (not full path) on success, or None on failure.
    """
    try:
        os.makedirs(backups_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        name = f"{prefix}researcharr-backup-{timestamp}.zip" if prefix else f"researcharr-backup-{timestamp}.zip"
        path = os.path.join(backups_dir, name)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            cfg = os.path.join(config_root, "config.yml")
            if os.path.exists(cfg):
                zf.write(cfg, arcname=os.path.join("config", "config.yml"))
            userf = os.path.join(config_root, "webui_user.yml")
            if os.path.exists(userf):
                zf.write(userf, arcname=os.path.join("config", "webui_user.yml"))
            dbf = os.path.join(config_root, "researcharr.db")
            if os.path.exists(dbf):
                zf.write(dbf, arcname=os.path.join("db", "researcharr.db"))
            plugins_dir = os.path.join(config_root, "plugins")
            if os.path.isdir(plugins_dir):
                for root, dirs, files in os.walk(plugins_dir):
                    for f in files:
                        full = os.path.join(root, f)
                        arc = os.path.join("plugins", os.path.relpath(full, plugins_dir))
                        zf.write(full, arcname=arc)
            app_log = os.path.join(os.path.dirname(__file__), os.pardir, "app.log")
            if os.path.exists(app_log):
                try:
                    zf.write(app_log, arcname=os.path.join("logs", "app.log"))
                except Exception:
                    pass
        return name
    except Exception:
        # Caller should log if desired; keep this module free of app logger
        return None


def prune_backups(backups_dir: str, cfg: Optional[dict] = None) -> None:
    """Prune backup files according to cfg.

    cfg is a mapping that may include:
      - retain_count: int (max number of newest backups to keep)
      - retain_days: int (remove backups older than this many days)
      - pre_restore_keep_days: int (keep pre-restore backups at least this many days)

    If cfg is None, nothing is removed.
    """
    try:
        if cfg is None:
            return
        retain_count = int(cfg.get("retain_count", 0) or 0)
        retain_days = int(cfg.get("retain_days", 0) or 0)
        pre_keep = int(cfg.get("pre_restore_keep_days", 1) or 1)
    except Exception:
        return

    try:
        if not os.path.isdir(backups_dir):
            return
        files = []
        for fname in os.listdir(backups_dir):
            fpath = os.path.join(backups_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                st = os.stat(fpath)
                files.append((fname, st.st_mtime))
            except Exception:
                continue
        # sort newest first
        files.sort(key=lambda x: x[1], reverse=True)

        now = time.time()
        # Remove by age first (if configured). Respect pre-restore keep window.
        if retain_days > 0:
            cutoff = now - (retain_days * 86400)
            for fname, mtime in list(files):
                if mtime < cutoff:
                    try:
                        if fname.startswith("pre-") and (now - mtime) < (pre_keep * 86400):
                            # keep recent pre-restore backups
                            continue
                        os.remove(os.path.join(backups_dir, fname))
                        files = [f for f in files if f[0] != fname]
                    except Exception:
                        # best-effort; continue
                        continue

        # Then enforce retain_count
        if retain_count > 0 and len(files) > retain_count:
            for fname, _ in files[retain_count:]:
                try:
                    os.remove(os.path.join(backups_dir, fname))
                except Exception:
                    continue
    except Exception:
        # best-effort
        return

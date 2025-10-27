import os
import zipfile
import time

from pathlib import Path

import pytest


def test_create_backup_includes_expected_files(tmp_path, monkeypatch):
    cfg_root = tmp_path / "cfg"
    cfg_root.mkdir()
    # create sample config and db and webui user
    (cfg_root / "config.yml").write_text("researcharr: {}\n")
    (cfg_root / "webui_user.yml").write_text("username: a\n")
    (cfg_root / "researcharr.db").write_text("sqlite")
    # plugin file
    plugins = cfg_root / "plugins"
    plugins.mkdir()
    (plugins / "pl.txt").write_text("p")

    backups_dir = tmp_path / "backups"

    import researcharr.backups as backups

    name = backups.create_backup_file(str(cfg_root), str(backups_dir), prefix="pre-")
    assert name is not None
    zip_path = backups_dir / name
    assert zip_path.exists()

    with zipfile.ZipFile(str(zip_path), "r") as z:
        namelist = z.namelist()
        assert "config/config.yml" in namelist
        assert "config/webui_user.yml" in namelist
        assert "db/researcharr.db" in namelist
        # plugin entry
        assert any(n.startswith("plugins/") for n in namelist)


def test_prune_backups_respects_retention(tmp_path):
    d = tmp_path / "backups"
    d.mkdir()
    # create files with different ages
    now = time.time()
    files = []
    for i in range(5):
        p = d / f"b{i}.zip"
        p.write_text("x")
        # set mtime staggered
        m = now - (i * 86400)
        os.utime(p, (m, m))
        files.append(p.name)

    # add a pre-restore file that is old but should be kept if within pre_restore_keep_days
    pre = d / "pre-old.zip"
    pre.write_text("y")
    pre_m = now - (2 * 86400)
    os.utime(pre, (pre_m, pre_m))

    import researcharr.backups as backups

    # prune by retain_count = 2 (should keep newest 2 plus possibly pre-keeping rules)
    cfg = {"retain_count": 2, "retain_days": 1, "pre_restore_keep_days": 3}
    backups.prune_backups(str(d), cfg)

    remaining = sorted([p.name for p in d.iterdir() if p.is_file()])
    # newest two should remain and pre-old should be kept because pre_keep_days=3 and it's 2 days old
    assert len(remaining) <= 3
    assert "pre-old.zip" in remaining
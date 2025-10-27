import os
import zipfile
from pathlib import Path

import pytest

from researcharr.backups import create_backup_file


def test_create_backup_includes_expected_files(tmp_path):
    config_root = tmp_path / "cfg"
    backups_dir = tmp_path / "backups"
    config_root.mkdir()
    backups_dir.mkdir()

    # create expected files
    (config_root / "config.yml").write_text("name: testconfig")
    (config_root / "webui_user.yml").write_text("user: test")
    (config_root / "researcharr.db").write_text("SQLITE")
    plugins = config_root / "plugins"
    plugins.mkdir()
    (plugins / "p1.py").write_text("# plugin")

    name = create_backup_file(str(config_root), str(backups_dir))
    assert name is not None
    zip_path = backups_dir / name
    assert zip_path.exists()

    # Inspect zip contents
    with zipfile.ZipFile(str(zip_path), "r") as zf:
        names = zf.namelist()
        assert "config/config.yml" in names
        assert "config/webui_user.yml" in names
        assert "db/researcharr.db" in names
        assert any(n.startswith("plugins/") for n in names)

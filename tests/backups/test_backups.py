import os
import zipfile

from researcharr.backups import (
    create_backup_file,
    get_backup_info,
    list_backups,
    prune_backups,
)


def test_create_and_list_backup(tmp_path):
    # prepare config tree
    cfg_root = tmp_path / "config"
    cfg_root.mkdir()
    (cfg_root / "config.yml").write_text("name: test")

    backups_dir = tmp_path / "backups"

    # create backup
    bp = create_backup_file(cfg_root, backups_dir, prefix="test-")
    assert bp is not None
    # Returned value should be path-like and exist on disk
    assert os.path.exists(str(bp))

    info = get_backup_info(bp)
    assert info is not None
    assert "files" in info

    listed = list_backups(backups_dir)
    assert isinstance(listed, list)
    assert any(item["name"].startswith("test-") for item in listed)


def test_prune_backups_by_count(tmp_path):
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()

    # create dummy zip files with distinct names
    for i in range(5):
        p = backups_dir / f"researcharr-backup-20250101T00000{i}Z.zip"
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("metadata.txt", "ok")

    # prune to retain only 2
    prune_backups(backups_dir, {"retain_count": 2, "retain_days": 0, "pre_restore_keep_days": 1})
    remaining = [e for e in backups_dir.iterdir() if e.is_file() and e.name.endswith(".zip")]
    assert len(remaining) <= 2

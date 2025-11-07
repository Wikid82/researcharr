import os
import sqlite3
import time
import zipfile

import pytest

import backups


def test_create_backup_nonexistent_no_prefix_raises(tmp_path):
    config_root = tmp_path / "nope"
    backups_dir = tmp_path / "backups"
    with pytest.raises(Exception):
        backups.create_backup_file(config_root, backups_dir)


def test_create_backup_with_prefix_creates_empty_zip(tmp_path):
    config_root = tmp_path / "nope"
    backups_dir = tmp_path / "backups"
    pathlike = backups.create_backup_file(config_root, backups_dir, prefix="pfx-")
    assert pathlike is not None
    # pathlike supports os.fspath and string methods via BackupPath
    assert str(pathlike).endswith(".zip")
    assert str(pathlike).startswith(str(backups_dir))
    # open the zip and assert metadata.txt present
    with zipfile.ZipFile(os.fspath(pathlike), "r") as zf:
        names = zf.namelist()
        assert "metadata.txt" in names


def test_create_backup_includes_db_snapshot(tmp_path):
    config_root = tmp_path / "config"
    config_root.mkdir()
    db_path = config_root / "researcharr.db"
    # create a simple sqlite db
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO t(name) VALUES (?)", ("x",))
    conn.commit()
    conn.close()

    backups_dir = tmp_path / "backups"
    pathlike = backups.create_backup_file(config_root, backups_dir)
    assert pathlike is not None
    with zipfile.ZipFile(os.fspath(pathlike), "r") as zf:
        namelist = zf.namelist()
        assert "db/researcharr.db" in namelist


def test_list_get_validate_size(tmp_path):
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    # create a small zip file
    p = backups_dir / "x.zip"
    with zipfile.ZipFile(str(p), "w") as zf:
        zf.writestr("metadata.txt", "ok")

    lst = backups.list_backups(backups_dir)
    assert any(e["name"] == "x.zip" for e in lst)

    info = backups.get_backup_info(p)
    assert info is not None and info["name"] == "x.zip"

    assert backups.validate_backup_file(p) is True
    assert backups.get_backup_size(p) > 0


def test_prune_by_count_and_days(tmp_path):
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    now = time.time()
    # create 4 files with different mtimes
    files = []
    for i, name in enumerate(["a.zip", "b.zip", "pre-old.zip", "c.zip"]):
        p = backups_dir / name
        with zipfile.ZipFile(str(p), "w") as zf:
            zf.writestr("metadata.txt", name)
        # modify mtime: newest first
        mtime = now - (i * 86400)
        os.utime(p, (mtime, mtime))
        files.append(p)

    # prune to retain_count=2
    backups.prune_backups(backups_dir, {"retain_count": 2})
    remaining = [p.name for p in backups_dir.iterdir() if p.is_file()]
    assert len(remaining) == 2

    # create an old file older than retain_days and ensure it is removed
    old = backups_dir / "old.zip"
    with zipfile.ZipFile(str(old), "w") as zf:
        zf.writestr("metadata.txt", "old")
    old_mtime = now - (10 * 86400)
    os.utime(old, (old_mtime, old_mtime))
    backups.prune_backups(backups_dir, {"retain_days": 1, "pre_restore_keep_days": 1})
    # old.zip should be removed
    names = [p.name for p in backups_dir.iterdir() if p.is_file()]
    assert "old.zip" not in names


def test_restore_backup_and_cleanup(tmp_path):
    # create a zip containing config/foo.txt
    zpath = tmp_path / "b.zip"
    with zipfile.ZipFile(str(zpath), "w") as zf:
        zf.writestr("config/foo.txt", "hello")

    dest = tmp_path / "dest"
    dest.mkdir()
    ok = backups.restore_backup(zpath, dest)
    assert ok is True
    # file should be restored at dest/foo.txt
    assert (dest / "foo.txt").exists()


def test_cleanup_temp_files(tmp_path):
    td = tmp_path / "tmpdir"
    td.mkdir()
    f = td / "t.tmp"
    f.write_text("x")
    d = td / "sub"
    d.mkdir()
    (d / "inner.txt").write_text("y")

    backups.cleanup_temp_files(td)
    # directory should now be empty
    assert list(td.iterdir()) == []


def test_default_and_merge_configs():
    d = backups.get_default_backup_config()
    assert "retain_count" in d
    merged = backups.merge_backup_configs(d, {"retain_count": 1})
    assert merged["retain_count"] == 1

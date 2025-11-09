import os
import sqlite3
import time
import zipfile


def test_create_backup_empty_prefix_behaviour(tmp_path):
    backups = tmp_path / "backups"
    # config root does not exist and no prefix -> should raise
    try:
        from researcharr.backups import create_backup_file

        raised = False
        try:
            create_backup_file(tmp_path / "noexist", backups)
        except Exception:
            raised = True
        assert raised
    finally:
        pass


def test_create_backup_with_prefix_and_db_snapshot(tmp_path):
    cfg = tmp_path / "config"
    cfg.mkdir()
    # create a simple sqlite DB so snapshot code runs
    db = cfg / "researcharr.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE IF NOT EXISTS t (i INTEGER)")
    conn.commit()
    conn.close()

    backups = tmp_path / "backups"
    from researcharr.backups import create_backup_file

    res = create_backup_file(cfg, backups, prefix="pre-")
    assert res is not None
    # returned object should behave like path and have basename starting with prefix
    s = str(res)
    assert "researcharr-backup-" in s
    # zip should exist and be a valid zipfile
    assert zipfile.is_zipfile(str(res))


def test_prune_backups_count_and_days(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    # create 5 backups with different mtimes
    files = []
    for i in range(5):
        p = backups / f"b{i}.zip"
        p.write_text("x")
        # set mtime spread by 1 day
        ts = time.time() - (i * 86400)
        os.utime(p, (ts, ts))
        files.append(p)

    from researcharr.backups import prune_backups

    # retain_count=2 should keep the two newest
    cfg = {"retain_count": 2}
    prune_backups(backups, cfg)
    remaining = [p.name for p in backups.iterdir() if p.is_file()]
    assert len(remaining) == 2

    # create some older pre- backups and test retain_days
    for i in range(3):
        p = backups / f"pre-old{i}.zip"
        p.write_text("y")
        ts = time.time() - (10 * 86400)
        os.utime(p, (ts, ts))

    cfg2 = {"retain_days": 1, "pre_restore_keep_days": 30}
    prune_backups(backups, cfg2)
    # pre-old should be kept because pre_restore_keep_days long enough
    assert any(n.startswith("pre-old") for n in [p.name for p in backups.iterdir()])


def test_get_list_info_size_and_validate(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    # create a zip file
    p = backups / "z1.zip"
    import zipfile

    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("config/config.yml", "a: 1")

    from researcharr.backups import (
        get_backup_info,
        get_backup_size,
        list_backups,
        validate_backup_file,
    )

    info = get_backup_info(p)
    assert info and info.get("name") == p.name
    lst = list_backups(backups)
    assert any(e["name"] == p.name for e in lst)
    assert validate_backup_file(p)
    assert get_backup_size(p) > 0


def test_restore_backup_and_cleanup(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    # create zip with config/config.yml
    p = backups / "r.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("config/config.yml", "ok: yes")

    dest = tmp_path / "dest"
    dest.mkdir()
    from researcharr.backups import restore_backup

    ok = restore_backup(p, dest)
    assert ok
    assert (dest / "config.yml").exists() or (dest / "config" / "config.yml").exists()

    # restore to non-existent dir should raise
    try:
        raised = False
        restore_backup(p, tmp_path / "nope")
    except Exception:
        raised = True
    assert raised


def test_cleanup_and_merge_and_defaults(tmp_path):
    t = tmp_path / "tmpdir"
    t.mkdir()
    f = t / "a.tmp"
    f.write_text("x")
    from researcharr.backups import (
        cleanup_temp_files,
        get_default_backup_config,
        merge_backup_configs,
    )

    cleanup_temp_files(t)
    # directory should be present but empty
    assert not any(t.iterdir())

    defaults = get_default_backup_config()
    merged = merge_backup_configs(defaults, {"retain_days": 7})
    assert merged.get("retain_days") == 7

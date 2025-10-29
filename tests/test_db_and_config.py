import sqlite3

from researcharr.researcharr import init_db, load_config


def test_init_db_creates_tables(tmp_path):
    dbpath = tmp_path / "test.db"
    init_db(str(dbpath))
    conn = sqlite3.connect(str(dbpath))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    conn.close()
    assert "radarr_queue" in tables and "sonarr_queue" in tables


def test_load_config_not_found():
    import pytest

    with pytest.raises(FileNotFoundError):
        load_config("this-file-does-not-exist.yml")


def test_load_config_empty(tmp_path):
    f = tmp_path / "cfg.yml"
    f.write_text("")
    cfg = load_config(str(f))
    assert cfg == {}

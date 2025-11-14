"""Tests for backup metadata, hot copy, and compatibility checks."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from researcharr import backups
from researcharr.storage.recovery import (
    get_alembic_head_revision,
    read_backup_meta,
)


@pytest.fixture()
def config_dir(tmp_path: Path):
    cfg = tmp_path / "config"
    cfg.mkdir()
    # Create SQLite DB
    db = cfg / "researcharr.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO t(v) VALUES('x')")
    con.commit()
    con.close()
    return cfg


def test_backup_contains_meta_and_hot_copy(config_dir: Path, tmp_path: Path):
    backups_dir = tmp_path / "backups"
    result = backups.create_backup_file(config_dir, backups_dir)
    assert result is not None
    meta = read_backup_meta(result)
    assert meta is not None
    assert "created" in meta
    assert "app_version" in meta
    # DB path present under db/ prefix
    import zipfile

    with zipfile.ZipFile(str(result), "r") as zf:
        names = zf.namelist()
        assert "db/researcharr.db" in names


def test_backup_meta_alembic_revision_optional(config_dir: Path, tmp_path: Path):
    backups_dir = tmp_path / "backups"
    result = backups.create_backup_file(config_dir, backups_dir)
    meta = read_backup_meta(result)
    # Revision may be None if alembic_version table absent
    assert "alembic_revision" in meta


def test_head_revision_detectable():
    head = get_alembic_head_revision()
    # Head should be a string revision id or None in edge cases
    assert head is None or isinstance(head, str)

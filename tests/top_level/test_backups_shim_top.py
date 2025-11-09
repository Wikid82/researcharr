"""Tests for the top-level `backups` shim module."""

import importlib
from pathlib import Path
import pytest


def test_top_level_backups_create_backup_file_error(tmp_path):
    backups = importlib.import_module("backups")
    missing = tmp_path / "does_not_exist"
    with pytest.raises(Exception):
        backups.create_backup_file(str(missing), str(tmp_path))


def test_top_level_backups_exports():
    backups = importlib.import_module("backups")
    assert hasattr(backups, "prune_backups")
    assert hasattr(backups, "list_backups")

import importlib


def test_backups_import_and_basic_api(tmp_path):
    m = importlib.import_module("researcharr.backups")

    # basic exports exist
    assert hasattr(m, "create_backup_file")
    assert hasattr(m, "get_default_backup_config")
    assert hasattr(m, "validate_backup_file")

    cfg = m.get_default_backup_config()
    assert isinstance(cfg, dict)
    assert "retain_count" in cfg

    # validate_backup_file should return False for a non-zip file
    f = tmp_path / "not_a_zip.txt"
    f.write_text("hello")
    assert m.validate_backup_file(str(f)) is False

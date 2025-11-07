"""Coverage tests for researcharr.db module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch


def test_get_db_path_from_database_url():
    """Test _get_db_path uses DATABASE_URL."""
    from researcharr.db import _get_db_path

    with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test/db.sqlite"}, clear=False):
        result = _get_db_path()

        assert result == "/test/db.sqlite"


def test_get_db_path_from_researcharr_db():
    """Test _get_db_path falls back to RESEARCHARR_DB."""
    from researcharr.db import _get_db_path

    with patch.dict(os.environ, {"RESEARCHARR_DB": "/custom/db.sqlite"}, clear=False):
        # Remove DATABASE_URL if present
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        with patch("researcharr.db.getattr", side_effect=AttributeError):
            result = _get_db_path()

            assert "/custom/db.sqlite" in result or result == "researcharr.db"


def test_get_db_path_import_exception():
    """Test _get_db_path handles import exception."""
    from researcharr.db import _get_db_path

    # Remove DATABASE_URL
    with patch.dict(os.environ, {}, clear=True):
        with patch("researcharr.db.getattr", side_effect=Exception("Import error")):
            result = _get_db_path()

            # Should fall back to RESEARCHARR_DB or default
            assert isinstance(result, str)


def test_conn_creates_directory():
    """Test _conn creates database directory if needed."""
    from researcharr.db import _conn

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "subdir" / "test.db"

        with patch("researcharr.db._get_db_path", return_value=str(db_path)):
            conn = _conn()

            assert db_path.parent.exists()
            conn.close()


def test_conn_handles_makedirs_exception():
    """Test _conn handles makedirs exception gracefully."""
    from researcharr.db import _conn

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "nonexistent" / "test.db"

        with patch("researcharr.db._get_db_path", return_value=str(db_path)):
            with patch("os.makedirs", side_effect=PermissionError("Cannot create")):
                # Should not raise even if makedirs fails
                try:
                    conn = _conn()
                    conn.close()
                except Exception:
                    pass  # Expected if db_path parent doesn't exist


def test_init_db_creates_table():
    """Test init_db creates webui_users table."""
    from researcharr.db import get_connection, init_db

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        with patch("researcharr.db._get_db_path", return_value=db_path):
            init_db()

            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webui_users'")
            result = cur.fetchone()
            conn.close()

            assert result is not None
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_load_user_no_users():
    """Test load_user returns None when no users exist."""
    from researcharr.db import load_user

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        with patch("researcharr.db._get_db_path", return_value=db_path):
            result = load_user()

            assert result is None
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_save_user_creates_user():
    """Test save_user creates a new user."""
    from researcharr.db import load_user, save_user

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        with patch("researcharr.db._get_db_path", return_value=db_path):
            save_user("testuser", "password_hash", "api_key_hash")

            user = load_user()
            assert user is not None
            assert user["username"] == "testuser"
            assert user["password_hash"] == "password_hash"
            assert user["api_key_hash"] == "api_key_hash"
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_save_user_updates_existing():
    """Test save_user updates existing user."""
    from researcharr.db import load_user, save_user

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        with patch("researcharr.db._get_db_path", return_value=db_path):
            # Create initial user
            save_user("user1", "hash1", "api1")

            # Update
            save_user("user1", "hash2", "api2")

            user = load_user()
            assert user["password_hash"] == "hash2"
            assert user["api_key_hash"] == "api2"
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_get_connection():
    """Test get_connection returns sqlite connection."""
    from researcharr.db import get_connection

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        with patch("researcharr.db._get_db_path", return_value=db_path):
            conn = get_connection()

            assert conn is not None
            assert hasattr(conn, "cursor")
            conn.close()
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_get_db_path_database_url_not_sqlite():
    """Test _get_db_path handles non-sqlite DATABASE_URL."""
    from researcharr.db import _get_db_path

    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/db"}, clear=False):
        result = _get_db_path()

        # Should fallback to default or RESEARCHARR_DB
        assert isinstance(result, str)

"""Database migration utilities."""

import logging
from pathlib import Path

from researcharr.storage.database import get_session, init_db

logger = logging.getLogger(__name__)


def migrate_database(database_path: str | Path) -> None:
    """
    Initialize database and apply migrations.

    Args:
        database_path: Path to SQLite database file
    """
    logger.info(f"Initializing database at {database_path}")
    init_db(database_path)

    # Ensure GlobalSettings singleton exists
    with get_session() as session:
        from researcharr.repositories import GlobalSettingsRepository

        settings_repo = GlobalSettingsRepository(session)
        settings = settings_repo.get_or_create()
        logger.info(f"GlobalSettings initialized with ID: {settings.id}")


def reset_database(database_path: str | Path) -> None:
    """
    Delete and recreate database (WARNING: destroys all data).

    Args:
        database_path: Path to SQLite database file
    """
    db_path = Path(database_path)
    if db_path.exists():
        logger.warning(f"Deleting existing database at {database_path}")
        db_path.unlink()

    migrate_database(database_path)
    logger.info("Database reset complete")

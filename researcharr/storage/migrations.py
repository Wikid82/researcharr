"""Database migration utilities."""

import logging
from pathlib import Path

from researcharr.storage.database import get_session, init_db

logger = logging.getLogger(__name__)


def migrate_database(database_path: str | Path, use_migrations: bool = True) -> None:
    """
    Initialize database and apply migrations.

    Args:
        database_path: Path to SQLite database file
        use_migrations: If True, use Alembic migrations. If False, use create_all().
    """
    logger.info(f"Initializing database at {database_path}")
    init_db(database_path, use_migrations=use_migrations)

    # Ensure GlobalSettings singleton exists without relying on any
    # cross-test cache state.
    with get_session() as session:
        from researcharr.storage.models import GlobalSettings

        settings = session.query(GlobalSettings).filter_by(id=1).first()
        if settings is None:
            settings = GlobalSettings(id=1)
            session.add(settings)
            session.flush()
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

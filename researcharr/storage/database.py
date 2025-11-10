"""Database session management and initialization."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

# Global session factory (initialized by init_db)
_session_factory: sessionmaker | None = None
_engine: Engine | None = None


def get_engine() -> Engine:
    """
    Get the current database engine.

    Returns:
        SQLAlchemy Engine instance

    Raises:
        RuntimeError: If database has not been initialized
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def init_db(database_path: str | Path, use_migrations: bool = True) -> None:
    """
    Initialize the database connection and create tables.

    Args:
        database_path: Path to the SQLite database file
        use_migrations: If True, use Alembic migrations (default).
                       If False, use create_all() for tests.
    """
    global _session_factory, _engine

    # Convert to Path and ensure parent directory exists
    db_path = Path(database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create engine with SQLite optimizations
    _engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},  # Allow multi-threaded access
        echo=False,  # Set to True for SQL query logging
    )

    # Check environment variable to override use_migrations
    env_use_migrations = os.getenv("RESEARCHARR_USE_MIGRATIONS", "true").lower()
    if env_use_migrations in ("false", "0", "no"):
        use_migrations = False

    if use_migrations:
        # Use Alembic migrations for production
        from alembic import command
        from alembic.config import Config

        # Find alembic.ini in the repo root
        repo_root = Path(__file__).parent.parent.parent
        alembic_ini = repo_root / "alembic.ini"

        if alembic_ini.exists():
            alembic_cfg = Config(str(alembic_ini))
            # Set the SQLAlchemy URL dynamically
            alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
            # Run migrations to latest
            command.upgrade(alembic_cfg, "head")
        else:
            # Fallback to create_all if alembic.ini not found
            Base.metadata.create_all(_engine)
    else:
        # Fast path for tests: direct table creation
        Base.metadata.create_all(_engine)

    # Create session factory
    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)


@contextmanager
def get_session() -> Generator[Session]:
    """
    Context manager for database sessions.

    Yields:
        SQLAlchemy Session object

    Raises:
        RuntimeError: If database has not been initialized

    Example:
        with get_session() as session:
            settings = session.query(GlobalSettings).first()
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

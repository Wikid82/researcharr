"""Database session management and initialization."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

# Global session factory (initialized by init_db)
_session_factory: sessionmaker | None = None


def init_db(database_path: str | Path) -> None:
    """
    Initialize the database connection and create tables.

    Args:
        database_path: Path to the SQLite database file
    """
    global _session_factory

    # Convert to Path and ensure parent directory exists
    db_path = Path(database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create engine with SQLite optimizations
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},  # Allow multi-threaded access
        echo=False,  # Set to True for SQL query logging
    )

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session factory
    _session_factory = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
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

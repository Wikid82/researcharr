"""Shared fixtures for repository tests."""

import pytest

from researcharr import cache as _cache
from researcharr.repositories import (
    GlobalSettingsRepository,
    ManagedAppRepository,
    ProcessingLogRepository,
    SearchCycleRepository,
    TrackedItemRepository,
)
from researcharr.storage.models import AppType, GlobalSettings, ManagedApp


@pytest.fixture(autouse=True)
def clear_repository_cache():
    """Ensure repository-level cache is cleared between tests."""
    _cache.clear_all()
    yield
    _cache.clear_all()


@pytest.fixture
def settings_repo(db_session):
    """Create GlobalSettingsRepository."""
    return GlobalSettingsRepository(db_session)


@pytest.fixture
def app_repo(db_session):
    """Create ManagedAppRepository."""
    return ManagedAppRepository(db_session)


@pytest.fixture
def item_repo(db_session):
    """Create TrackedItemRepository."""
    return TrackedItemRepository(db_session)


@pytest.fixture
def cycle_repo(db_session):
    """Create SearchCycleRepository."""
    return SearchCycleRepository(db_session)


@pytest.fixture
def log_repo(db_session):
    """Create ProcessingLogRepository."""
    return ProcessingLogRepository(db_session)


@pytest.fixture
def sample_settings(db_session):
    """Create sample GlobalSettings."""
    settings = GlobalSettings(id=1)
    db_session.add(settings)
    db_session.commit()
    return settings


@pytest.fixture
def sample_radarr_app(db_session):
    """Create sample Radarr app."""
    app = ManagedApp(
        app_type=AppType.RADARR,
        name="Test Radarr",
        base_url="http://localhost:7878",
        api_key="test_radarr_key",
    )
    db_session.add(app)
    db_session.commit()
    return app


@pytest.fixture
def sample_sonarr_app(db_session):
    """Create sample Sonarr app."""
    app = ManagedApp(
        app_type=AppType.SONARR,
        name="Test Sonarr",
        base_url="http://localhost:8989",
        api_key="test_sonarr_key",
    )
    db_session.add(app)
    db_session.commit()
    return app

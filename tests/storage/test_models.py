"""Tests for SQLAlchemy models."""

import pytest

from researcharr.storage.models import (
    AppType,
    CyclePhase,
    GlobalSettings,
    ManagedApp,
    ProcessingLog,
    SearchCycle,
    SortStrategy,
    TrackedItem,
)


def test_global_settings_defaults(db_session):
    """Test GlobalSettings model with default values."""
    settings = GlobalSettings(id=1)
    db_session.add(settings)
    db_session.commit()

    assert settings.id == 1
    assert settings.items_per_cycle == 5
    assert settings.cycle_interval_minutes == 60
    assert settings.state_management_period_days == 7
    assert settings.sort_strategy == SortStrategy.CUSTOM_FORMAT_SCORE_ASC
    assert settings.retry_failed_items is True
    assert settings.max_retries == 3
    assert settings.retry_delay_minutes == 120
    assert settings.notifications_enabled is True
    assert settings.created_at is not None
    assert settings.updated_at is not None


def test_global_settings_singleton(db_session):
    """Test GlobalSettings singleton pattern."""
    settings1 = GlobalSettings(id=1)
    db_session.add(settings1)
    db_session.commit()

    # Query back
    retrieved = db_session.query(GlobalSettings).filter(GlobalSettings.id == 1).first()
    assert retrieved is not None
    assert retrieved.id == 1


def test_managed_app_creation(db_session):
    """Test ManagedApp model creation."""
    app = ManagedApp(
        app_type=AppType.RADARR,
        name="Test Radarr",
        base_url="http://localhost:7878",
        api_key="test_api_key",
        is_active=True,
    )
    db_session.add(app)
    db_session.commit()

    assert app.id is not None
    assert app.app_type == AppType.RADARR
    assert app.name == "Test Radarr"
    assert app.use_custom_settings is False
    assert app.custom_items_per_cycle is None


def test_managed_app_with_custom_settings(db_session):
    """Test ManagedApp with custom settings override."""
    app = ManagedApp(
        app_type=AppType.SONARR,
        name="Test Sonarr",
        base_url="http://localhost:8989",
        api_key="test_api_key",
        use_custom_settings=True,
        custom_items_per_cycle=10,
        custom_sort_strategy=SortStrategy.ALPHABETICAL_ASC,
    )
    db_session.add(app)
    db_session.commit()

    assert app.use_custom_settings is True
    assert app.custom_items_per_cycle == 10
    assert app.custom_sort_strategy == SortStrategy.ALPHABETICAL_ASC


def test_tracked_item_creation(db_session):
    """Test TrackedItem model creation."""
    app = ManagedApp(
        app_type=AppType.RADARR,
        name="Test Radarr",
        base_url="http://localhost:7878",
        api_key="test_key",
    )
    db_session.add(app)
    db_session.commit()

    item = TrackedItem(
        app_id=app.id,
        arr_id=123,
        tmdb_id=456,
        title="Test Movie",
        year=2024,
        monitored=True,
        has_file=False,
        custom_format_score=85.5,
    )
    db_session.add(item)
    db_session.commit()

    assert item.id is not None
    assert item.app_id == app.id
    assert item.arr_id == 123
    assert item.tmdb_id == 456
    assert item.tvdb_id is None  # Not set for Radarr
    assert item.search_count == 0
    assert item.failed_search_count == 0


def test_tracked_item_relationships(db_session):
    """Test TrackedItem relationships with ManagedApp."""
    app = ManagedApp(
        app_type=AppType.SONARR,
        name="Test Sonarr",
        base_url="http://localhost:8989",
        api_key="test_key",
    )
    db_session.add(app)
    db_session.commit()

    item1 = TrackedItem(app_id=app.id, arr_id=1, title="Series 1", monitored=True)
    item2 = TrackedItem(app_id=app.id, arr_id=2, title="Series 2", monitored=True)
    db_session.add_all([item1, item2])
    db_session.commit()

    # Test relationship
    retrieved_app = db_session.query(ManagedApp).filter(ManagedApp.id == app.id).first()
    assert len(retrieved_app.tracked_items) == 2


def test_search_cycle_creation(db_session):
    """Test SearchCycle model creation."""
    app = ManagedApp(
        app_type=AppType.RADARR,
        name="Test Radarr",
        base_url="http://localhost:7878",
        api_key="test_key",
    )
    db_session.add(app)
    db_session.commit()

    cycle = SearchCycle(
        app_id=app.id,
        cycle_number=1,
        phase=CyclePhase.SYNCING,
        total_items=10,
    )
    db_session.add(cycle)
    db_session.commit()

    assert cycle.id is not None
    assert cycle.cycle_number == 1
    assert cycle.phase == CyclePhase.SYNCING
    assert cycle.items_searched == 0
    assert cycle.completed_at is None


def test_processing_log_creation(db_session):
    """Test ProcessingLog model creation."""
    app = ManagedApp(
        app_type=AppType.RADARR,
        name="Test Radarr",
        base_url="http://localhost:7878",
        api_key="test_key",
    )
    db_session.add(app)
    db_session.commit()

    log = ProcessingLog(
        app_id=app.id,
        event_type="search_started",
        message="Search started for Test Movie",
        success=True,
    )
    db_session.add(log)
    db_session.commit()

    assert log.id is not None
    assert log.app_id == app.id
    assert log.event_type == "search_started"
    assert log.success is True
    assert log.tracked_item_id is None


def test_unique_constraints(db_session):
    """Test unique constraints on models."""
    app = ManagedApp(
        app_type=AppType.RADARR,
        name="Test Radarr",
        base_url="http://localhost:7878",
        api_key="test_key",
    )
    db_session.add(app)
    db_session.commit()

    # Try to create duplicate app
    duplicate_app = ManagedApp(
        app_type=AppType.RADARR,
        name="Another Radarr",
        base_url="http://localhost:7878",  # Same URL and type
        api_key="different_key",
    )
    db_session.add(duplicate_app)

    with pytest.raises(Exception):  # Should raise IntegrityError
        db_session.commit()


def test_cascade_delete(db_session):
    """Test cascade delete on related entities."""
    app = ManagedApp(
        app_type=AppType.RADARR,
        name="Test Radarr",
        base_url="http://localhost:7878",
        api_key="test_key",
    )
    db_session.add(app)
    db_session.commit()

    item = TrackedItem(app_id=app.id, arr_id=1, title="Test Movie", monitored=True)
    db_session.add(item)
    db_session.commit()

    item_id = item.id

    # Delete app
    db_session.delete(app)
    db_session.commit()

    # Item should be deleted due to cascade
    deleted_item = db_session.query(TrackedItem).filter(TrackedItem.id == item_id).first()
    assert deleted_item is None


def test_enum_values(db_session):
    """Test enum types in models."""
    # Test AppType
    assert AppType.RADARR.value == "radarr"
    assert AppType.SONARR.value == "sonarr"

    # Test SortStrategy
    assert SortStrategy.CUSTOM_FORMAT_SCORE_ASC.value == "custom_format_score_asc"
    assert SortStrategy.EXTERNAL_ID_ASC.value == "external_id_asc"

    # Test CyclePhase
    assert CyclePhase.SYNCING.value == "syncing"
    assert CyclePhase.SEARCHING.value == "searching"
    assert CyclePhase.COOLDOWN.value == "cooldown"
    assert CyclePhase.RESETTING.value == "resetting"

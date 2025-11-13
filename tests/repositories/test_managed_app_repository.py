"""Tests for ManagedAppRepository."""

from researcharr.storage.models import AppType, ManagedApp


def test_create_app(app_repo):
    """Test creating a new managed app."""
    app = ManagedApp(
        app_type=AppType.RADARR,
        name="My Radarr",
        base_url="http://localhost:7878",
        api_key="secret_key",
    )
    created = app_repo.create(app)

    assert created.id is not None
    assert created.name == "My Radarr"
    assert created.is_active is True


def test_get_by_id(app_repo, sample_radarr_app):
    """Test getting app by ID."""
    app = app_repo.get_by_id(sample_radarr_app.id)

    assert app is not None
    assert app.id == sample_radarr_app.id
    assert app.name == "Test Radarr"


def test_get_all(app_repo, sample_radarr_app, sample_sonarr_app):
    """Test getting all apps."""
    apps = app_repo.get_all()

    assert len(apps) == 2
    app_types = {app.app_type for app in apps}
    assert AppType.RADARR in app_types
    assert AppType.SONARR in app_types


def test_get_active_apps(app_repo, sample_radarr_app, sample_sonarr_app, db_session):
    """Test getting only active apps."""
    # Deactivate Sonarr
    sample_sonarr_app.is_active = False
    db_session.commit()

    active_apps = app_repo.get_active_apps()

    assert len(active_apps) == 1
    assert active_apps[0].app_type == AppType.RADARR


def test_get_by_type(app_repo, sample_radarr_app, sample_sonarr_app):
    """Test getting apps by type."""
    radarr_apps = app_repo.get_by_type(AppType.RADARR)
    sonarr_apps = app_repo.get_by_type(AppType.SONARR)

    assert len(radarr_apps) == 1
    assert len(sonarr_apps) == 1
    assert radarr_apps[0].app_type == AppType.RADARR
    assert sonarr_apps[0].app_type == AppType.SONARR


def test_get_by_url(app_repo, sample_radarr_app):
    """Test getting app by URL and type."""
    app = app_repo.get_by_url("http://localhost:7878", AppType.RADARR)

    assert app is not None
    assert app.id == sample_radarr_app.id


def test_update_app(app_repo, sample_radarr_app):
    """Test updating an app."""
    sample_radarr_app.name = "Updated Radarr"
    sample_radarr_app.use_custom_settings = True
    sample_radarr_app.custom_items_per_cycle = 15

    updated = app_repo.update(sample_radarr_app)

    assert updated.name == "Updated Radarr"
    assert updated.use_custom_settings is True
    assert updated.custom_items_per_cycle == 15


def test_delete_app(app_repo, sample_radarr_app):
    """Test deleting an app."""
    app_id = sample_radarr_app.id
    result = app_repo.delete(app_id)

    assert result is True
    assert app_repo.get_by_id(app_id) is None


def test_delete_nonexistent_app(app_repo):
    """Test deleting non-existent app returns False."""
    result = app_repo.delete(9999)

    assert result is False

"""Tests for GlobalSettingsRepository."""

from researcharr.storage.models import SortStrategy


def test_get_or_create_creates_new(settings_repo):
    """Test get_or_create creates new settings if none exist."""
    settings = settings_repo.get_or_create()

    assert settings.id == 1
    assert settings.items_per_cycle == 5
    assert settings.notifications_enabled is True


def test_get_or_create_returns_existing(settings_repo, sample_settings):
    """Test get_or_create returns existing settings."""
    settings = settings_repo.get_or_create()

    assert settings.id == sample_settings.id


def test_update_settings(settings_repo, sample_settings):
    """Test updating global settings."""
    sample_settings.items_per_cycle = 10
    sample_settings.sort_strategy = SortStrategy.ALPHABETICAL_ASC

    updated = settings_repo.update(sample_settings)

    assert updated.items_per_cycle == 10
    assert updated.sort_strategy == SortStrategy.ALPHABETICAL_ASC


def test_get_by_id(settings_repo, sample_settings):
    """Test getting settings by ID."""
    settings = settings_repo.get_by_id(1)

    assert settings is not None
    assert settings.id == 1


def test_get_all_returns_single_item(settings_repo, sample_settings):
    """Test get_all returns singleton list."""
    all_settings = settings_repo.get_all()

    assert len(all_settings) == 1
    assert all_settings[0].id == 1

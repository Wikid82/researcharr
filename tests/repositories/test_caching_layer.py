"""Caching layer tests for repositories."""

import os

from researcharr.cache import clear_all
from researcharr.repositories.global_settings import GlobalSettingsRepository
from researcharr.repositories.managed_app import ManagedAppRepository
from researcharr.storage.database import get_session, init_db
from researcharr.storage.models import AppType, ManagedApp


def setup_module(module):
    # Ensure caching is enabled
    os.environ.pop("RESEARCHARR_CACHE_DISABLED", None)


def setup_db(tmp_path):
    db_file = tmp_path / "cache.db"
    init_db(db_file, use_migrations=False)
    clear_all()
    return db_file


def test_global_settings_cached(tmp_path):
    setup_db(tmp_path)
    with get_session() as session:
        repo = GlobalSettingsRepository(session)
        # First call creates and caches
        s1 = repo.get_or_create()
        # Second call should hit cache (same identity)
        s2 = repo.get_or_create()
        assert s1.id == s2.id == 1
        # Update should invalidate cache
        s1.items_per_cycle = 7
        repo.update(s1)
        s3 = repo.get_or_create()
        assert s3.items_per_cycle == 7


def test_managed_app_caching_and_invalidation(tmp_path):
    setup_db(tmp_path)
    with get_session() as session:
        repo = ManagedAppRepository(session)
        app = ManagedApp(app_type=AppType.RADARR, name="a1", base_url="http://a", api_key="k")
        repo.create(app)
        # Prime caches
        a = repo.get_by_id(app.id)
        assert a is not None
        active = repo.get_active_apps()
        assert any(x.id == app.id for x in active)
        by_type = repo.get_by_type(AppType.RADARR)
        assert any(x.id == app.id for x in by_type)
        by_url = repo.get_by_url("http://a", AppType.RADARR)
        assert by_url is not None
        # Update should invalidate all ManagedApp caches
        app.name = "a1b"
        repo.update(app)
        a2 = repo.get_by_id(app.id)
        assert a2 is not None and a2.name == "a1b"

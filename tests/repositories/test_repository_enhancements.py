"""Enhanced repository behavior: bulk ops, pagination, aggregations, eager loading."""

from datetime import datetime, timedelta

from researcharr.repositories.managed_app import ManagedAppRepository
from researcharr.repositories.processing_log import ProcessingLogRepository
from researcharr.repositories.search_cycle import SearchCycleRepository
from researcharr.repositories.tracked_item import TrackedItemRepository
from researcharr.storage.database import get_session, init_db
from researcharr.storage.models import (
    AppType,
    ManagedApp,
    ProcessingLog,
    SearchCycle,
    TrackedItem,
)


def setup_db(tmp_path):
    db_file = tmp_path / "enhanced.db"
    init_db(db_file, use_migrations=False)
    return db_file


def test_bulk_create_and_paginate_tracked_items(tmp_path):
    setup_db(tmp_path)
    with get_session() as session:
        # Create an app
        app = ManagedApp(app_type=AppType.RADARR, name="radarr-1", base_url="http://a", api_key="k")
        session.add(app)
        session.flush()
        repo = TrackedItemRepository(session)
        # Bulk create 25 items
        items = [TrackedItem(app_id=app.id, arr_id=i, title=f"Title {i}") for i in range(1, 26)]
        repo.bulk_create(items)
        # Paginate: page 2 of size 10
        page2 = repo.get_page(page=2, page_size=10)
        assert len(page2) == 10
        ids = {ti.id for ti in page2}
        assert len(ids) == 10


def test_bulk_upsert_updates_values(tmp_path):
    setup_db(tmp_path)
    with get_session() as session:
        app = ManagedApp(app_type=AppType.SONARR, name="sonarr-1", base_url="http://b", api_key="k")
        session.add(app)
        session.flush()
        repo = TrackedItemRepository(session)
        item = TrackedItem(app_id=app.id, arr_id=101, title="Old")
        repo.create(item)
        # Upsert with changed title
        merged = repo.bulk_upsert([TrackedItem(id=item.id, app_id=app.id, arr_id=101, title="New")])
        assert merged[0].title == "New"


def test_processing_log_aggregations(tmp_path):
    setup_db(tmp_path)
    with get_session() as session:
        app = ManagedApp(app_type=AppType.RADARR, name="radarr-2", base_url="http://c", api_key="k")
        session.add(app)
        session.flush()
        logs = ProcessingLogRepository(session)
        now = datetime.utcnow()
        # Insert diverse events
        session.add_all(
            [
                ProcessingLog(
                    app_id=app.id,
                    event_type="search_started",
                    message="m",
                    success=True,
                    created_at=now,
                ),
                ProcessingLog(
                    app_id=app.id,
                    event_type="search_completed",
                    message="m",
                    success=True,
                    created_at=now,
                ),
                ProcessingLog(
                    app_id=app.id,
                    event_type="search_failed",
                    message="m",
                    success=False,
                    created_at=now,
                ),
                ProcessingLog(
                    app_id=app.id,
                    event_type="search_failed",
                    message="m",
                    success=False,
                    created_at=now - timedelta(days=1),
                ),
            ]
        )
        session.flush()
        counts = logs.get_event_counts(app.id)
        assert counts.get("search_failed") == 2
        rate = logs.get_success_rate(app.id)
        assert 0.0 <= rate <= 1.0
        # Since filter should exclude one older failed event
        counts_since = logs.get_event_counts(app.id, since=now - timedelta(hours=1))
        assert counts_since.get("search_failed") == 1


def test_search_cycle_recent_for_app(tmp_path):
    setup_db(tmp_path)
    with get_session() as session:
        app = ManagedApp(app_type=AppType.SONARR, name="sonarr-2", base_url="http://d", api_key="k")
        session.add(app)
        session.flush()
        cycles = SearchCycleRepository(session)
        # Create cycles with different started_at
        c1 = SearchCycle(
            app_id=app.id, cycle_number=1, started_at=datetime.utcnow() - timedelta(days=2)
        )
        c2 = SearchCycle(
            app_id=app.id, cycle_number=2, started_at=datetime.utcnow() - timedelta(days=1)
        )
        c3 = SearchCycle(app_id=app.id, cycle_number=3, started_at=datetime.utcnow())
        session.add_all([c1, c2, c3])
        session.flush()
        recent = cycles.get_recent_for_app(app.id, limit=2)
        assert len(recent) == 2
        assert recent[0].cycle_number == 3
        assert recent[1].cycle_number == 2


def test_managed_app_pagination_and_eager(tmp_path):
    setup_db(tmp_path)
    with get_session() as session:
        apps_repo = ManagedAppRepository(session)
        # Create 12 apps
        apps = [
            ManagedApp(
                app_type=AppType.RADARR, name=f"app-{i}", base_url=f"http://{i}", api_key="k"
            )
            for i in range(12)
        ]
        apps_repo.bulk_create(apps)
        page = apps_repo.get_page(page=2, page_size=5)
        assert len(page) == 5
        # Eager loading check for tracked_item get_by_id
        # Create an item for the first app and fetch with repo
        item_repo = TrackedItemRepository(session)
        item = TrackedItem(app_id=apps[0].id, arr_id=999, title="Eager")
        item_repo.create(item)
        fetched = item_repo.get_by_id(item.id)
        assert fetched is not None and fetched.app is not None

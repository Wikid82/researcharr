"""Tests for TrackedItemRepository."""

from datetime import datetime, timedelta

from researcharr.storage.models import SortStrategy, TrackedItem


def test_create_tracked_item(item_repo, sample_radarr_app):
    """Test creating a tracked item."""
    item = TrackedItem(
        app_id=sample_radarr_app.id,
        arr_id=123,
        tmdb_id=456,
        title="Test Movie",
        monitored=True,
    )
    created = item_repo.create(item)

    assert created.id is not None
    assert created.arr_id == 123
    assert created.search_count == 0


def test_get_by_app(item_repo, sample_radarr_app, sample_sonarr_app, db_session):
    """Test getting items by app."""
    item1 = TrackedItem(app_id=sample_radarr_app.id, arr_id=1, title="Movie 1", monitored=True)
    item2 = TrackedItem(app_id=sample_radarr_app.id, arr_id=2, title="Movie 2", monitored=True)
    item3 = TrackedItem(app_id=sample_sonarr_app.id, arr_id=1, title="Series 1", monitored=True)
    db_session.add_all([item1, item2, item3])
    db_session.commit()

    radarr_items = item_repo.get_by_app(sample_radarr_app.id)
    sonarr_items = item_repo.get_by_app(sample_sonarr_app.id)

    assert len(radarr_items) == 2
    assert len(sonarr_items) == 1


def test_get_by_arr_id(item_repo, sample_radarr_app, db_session):
    """Test getting item by arr_id."""
    item = TrackedItem(
        app_id=sample_radarr_app.id, arr_id=999, title="Unique Movie", monitored=True
    )
    db_session.add(item)
    db_session.commit()

    found = item_repo.get_by_arr_id(sample_radarr_app.id, 999)

    assert found is not None
    assert found.arr_id == 999


def test_get_items_for_search_by_score(item_repo, sample_radarr_app, db_session):
    """Test getting items sorted by custom format score."""
    items = [
        TrackedItem(
            app_id=sample_radarr_app.id,
            arr_id=1,
            title="Low Score",
            monitored=True,
            custom_format_score=10.0,
        ),
        TrackedItem(
            app_id=sample_radarr_app.id,
            arr_id=2,
            title="High Score",
            monitored=True,
            custom_format_score=90.0,
        ),
        TrackedItem(
            app_id=sample_radarr_app.id,
            arr_id=3,
            title="Mid Score",
            monitored=True,
            custom_format_score=50.0,
        ),
    ]
    db_session.add_all(items)
    db_session.commit()

    # Get items sorted ascending (lowest score first)
    results = item_repo.get_items_for_search(
        sample_radarr_app.id, SortStrategy.CUSTOM_FORMAT_SCORE_ASC, limit=3, include_retries=False
    )

    assert len(results) == 3
    assert results[0].custom_format_score == 10.0
    assert results[1].custom_format_score == 50.0
    assert results[2].custom_format_score == 90.0


def test_get_items_for_search_alphabetical(item_repo, sample_radarr_app, db_session):
    """Test getting items sorted alphabetically."""
    items = [
        TrackedItem(app_id=sample_radarr_app.id, arr_id=1, title="Zebra", monitored=True),
        TrackedItem(app_id=sample_radarr_app.id, arr_id=2, title="Apple", monitored=True),
        TrackedItem(app_id=sample_radarr_app.id, arr_id=3, title="Mango", monitored=True),
    ]
    db_session.add_all(items)
    db_session.commit()

    results = item_repo.get_items_for_search(
        sample_radarr_app.id, SortStrategy.ALPHABETICAL_ASC, limit=3, include_retries=False
    )

    assert len(results) == 3
    assert results[0].title == "Apple"
    assert results[1].title == "Mango"
    assert results[2].title == "Zebra"


def test_get_items_for_search_external_id(item_repo, sample_radarr_app, db_session):
    """Test getting items sorted by external ID."""
    items = [
        TrackedItem(
            app_id=sample_radarr_app.id, arr_id=1, title="Movie 1", monitored=True, tmdb_id=300
        ),
        TrackedItem(
            app_id=sample_radarr_app.id, arr_id=2, title="Movie 2", monitored=True, tmdb_id=100
        ),
        TrackedItem(
            app_id=sample_radarr_app.id, arr_id=3, title="Movie 3", monitored=True, tmdb_id=200
        ),
    ]
    db_session.add_all(items)
    db_session.commit()

    results = item_repo.get_items_for_search(
        sample_radarr_app.id, SortStrategy.EXTERNAL_ID_ASC, limit=3, include_retries=False
    )

    assert len(results) == 3
    assert results[0].tmdb_id == 100
    assert results[1].tmdb_id == 200
    assert results[2].tmdb_id == 300


def test_get_items_for_search_limit(item_repo, sample_radarr_app, db_session):
    """Test limit parameter works correctly."""
    items = [
        TrackedItem(app_id=sample_radarr_app.id, arr_id=i, title=f"Movie {i}", monitored=True)
        for i in range(10)
    ]
    db_session.add_all(items)
    db_session.commit()

    results = item_repo.get_items_for_search(
        sample_radarr_app.id, SortStrategy.ALPHABETICAL_ASC, limit=5, include_retries=False
    )

    assert len(results) == 5


def test_get_items_for_search_excludes_with_files(item_repo, sample_radarr_app, db_session):
    """Test that items with files are excluded."""
    items = [
        TrackedItem(
            app_id=sample_radarr_app.id, arr_id=1, title="No File", monitored=True, has_file=False
        ),
        TrackedItem(
            app_id=sample_radarr_app.id, arr_id=2, title="Has File", monitored=True, has_file=True
        ),
    ]
    db_session.add_all(items)
    db_session.commit()

    results = item_repo.get_items_for_search(
        sample_radarr_app.id, SortStrategy.ALPHABETICAL_ASC, limit=10, include_retries=False
    )

    assert len(results) == 1
    assert results[0].title == "No File"


def test_get_items_for_search_excludes_unmonitored(item_repo, sample_radarr_app, db_session):
    """Test that unmonitored items are excluded."""
    items = [
        TrackedItem(app_id=sample_radarr_app.id, arr_id=1, title="Monitored", monitored=True),
        TrackedItem(app_id=sample_radarr_app.id, arr_id=2, title="Unmonitored", monitored=False),
    ]
    db_session.add_all(items)
    db_session.commit()

    results = item_repo.get_items_for_search(
        sample_radarr_app.id, SortStrategy.ALPHABETICAL_ASC, limit=10, include_retries=False
    )

    assert len(results) == 1
    assert results[0].title == "Monitored"


def test_get_items_for_search_with_retries(item_repo, sample_radarr_app, db_session):
    """Test including items in retry queue."""
    now = datetime.utcnow()
    items = [
        TrackedItem(
            app_id=sample_radarr_app.id,
            arr_id=1,
            title="Never Searched",
            monitored=True,
            last_search_at=None,
        ),
        TrackedItem(
            app_id=sample_radarr_app.id,
            arr_id=2,
            title="Ready for Retry",
            monitored=True,
            last_search_at=now - timedelta(hours=2),
            next_retry_at=now - timedelta(minutes=10),  # Ready now
        ),
        TrackedItem(
            app_id=sample_radarr_app.id,
            arr_id=3,
            title="Not Ready for Retry",
            monitored=True,
            last_search_at=now - timedelta(hours=1),
            next_retry_at=now + timedelta(hours=1),  # Not ready yet
        ),
    ]
    db_session.add_all(items)
    db_session.commit()

    results = item_repo.get_items_for_search(
        sample_radarr_app.id, SortStrategy.ALPHABETICAL_ASC, limit=10, include_retries=True
    )

    # Should include: Never Searched + Ready for Retry
    assert len(results) == 2
    titles = {item.title for item in results}
    assert "Never Searched" in titles
    assert "Ready for Retry" in titles


def test_get_retry_queue_size(item_repo, sample_radarr_app, db_session):
    """Test counting items in retry queue."""
    now = datetime.utcnow()
    items = [
        TrackedItem(
            app_id=sample_radarr_app.id,
            arr_id=1,
            title="Ready 1",
            monitored=True,
            next_retry_at=now - timedelta(minutes=10),
        ),
        TrackedItem(
            app_id=sample_radarr_app.id,
            arr_id=2,
            title="Ready 2",
            monitored=True,
            next_retry_at=now - timedelta(minutes=5),
        ),
        TrackedItem(
            app_id=sample_radarr_app.id,
            arr_id=3,
            title="Not Ready",
            monitored=True,
            next_retry_at=now + timedelta(hours=1),
        ),
    ]
    db_session.add_all(items)
    db_session.commit()

    count = item_repo.get_retry_queue_size(sample_radarr_app.id)

    assert count == 2


def test_mark_searched_success(item_repo, sample_radarr_app, db_session):
    """Test marking item as successfully searched."""
    item = TrackedItem(app_id=sample_radarr_app.id, arr_id=1, title="Test", monitored=True)
    db_session.add(item)
    db_session.commit()

    updated = item_repo.mark_searched(item.id, success=True)

    assert updated.search_count == 1
    assert updated.failed_search_count == 0
    assert updated.last_search_at is not None
    assert updated.next_retry_at is None


def test_mark_searched_failure(item_repo, sample_radarr_app, db_session):
    """Test marking item as failed search with retry."""
    item = TrackedItem(app_id=sample_radarr_app.id, arr_id=1, title="Test", monitored=True)
    db_session.add(item)
    db_session.commit()

    retry_time = datetime.utcnow() + timedelta(hours=2)
    updated = item_repo.mark_searched(item.id, success=False, next_retry_at=retry_time)

    assert updated.search_count == 1
    assert updated.failed_search_count == 1
    assert updated.next_retry_at == retry_time


def test_update_tracked_item(item_repo, sample_radarr_app, db_session):
    """Test updating a tracked item."""
    item = TrackedItem(
        app_id=sample_radarr_app.id,
        arr_id=1,
        title="Old Title",
        monitored=True,
        custom_format_score=50.0,
    )
    db_session.add(item)
    db_session.commit()

    item.title = "New Title"
    item.custom_format_score = 75.0
    updated = item_repo.update(item)

    assert updated.title == "New Title"
    assert updated.custom_format_score == 75.0

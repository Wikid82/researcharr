"""Tests for ProcessingLogRepository."""

import json
from datetime import datetime, timedelta

from researcharr.storage.models import TrackedItem


def test_log_event(log_repo, sample_radarr_app):
    """Test creating a log event."""
    log = log_repo.log_event(
        app_id=sample_radarr_app.id,
        event_type="search_started",
        message="Search started for Test Movie",
        success=True,
    )

    assert log.id is not None
    assert log.app_id == sample_radarr_app.id
    assert log.event_type == "search_started"
    assert log.success is True


def test_log_event_with_item(log_repo, sample_radarr_app, db_session):
    """Test creating log with tracked item reference."""
    item = TrackedItem(app_id=sample_radarr_app.id, arr_id=123, title="Test Movie", monitored=True)
    db_session.add(item)
    db_session.commit()

    log = log_repo.log_event(
        app_id=sample_radarr_app.id,
        tracked_item_id=item.id,
        event_type="search_completed",
        message="Search completed",
        success=True,
    )

    assert log.tracked_item_id == item.id


def test_log_event_with_details(log_repo, sample_radarr_app):
    """Test creating log with JSON details."""
    details = {"releases_found": 5, "quality": "1080p"}
    log = log_repo.log_event(
        app_id=sample_radarr_app.id,
        event_type="search_completed",
        message="Search found releases",
        success=True,
        details=json.dumps(details),
    )

    assert log.details is not None
    parsed = json.loads(log.details)
    assert parsed["releases_found"] == 5


def test_get_by_app(log_repo, sample_radarr_app, sample_sonarr_app, db_session):
    """Test getting logs by app."""
    log_repo.log_event(sample_radarr_app.id, "event1", "Radarr event")
    log_repo.log_event(sample_radarr_app.id, "event2", "Another Radarr event")
    log_repo.log_event(sample_sonarr_app.id, "event1", "Sonarr event")
    db_session.commit()

    radarr_logs = log_repo.get_by_app(sample_radarr_app.id)
    sonarr_logs = log_repo.get_by_app(sample_sonarr_app.id)

    assert len(radarr_logs) == 2
    assert len(sonarr_logs) == 1


def test_get_by_app_limit(log_repo, sample_radarr_app, db_session):
    """Test limit parameter on get_by_app."""
    for i in range(10):
        log_repo.log_event(sample_radarr_app.id, f"event_{i}", f"Event {i}")
    db_session.commit()

    logs = log_repo.get_by_app(sample_radarr_app.id, limit=5)

    assert len(logs) == 5


def test_get_by_app_ordered_by_time(log_repo, sample_radarr_app, db_session):
    """Test logs are ordered by created_at descending."""
    log1 = log_repo.log_event(sample_radarr_app.id, "event1", "First")
    db_session.commit()

    # Wait a moment
    import time

    time.sleep(0.01)

    log2 = log_repo.log_event(sample_radarr_app.id, "event2", "Second")
    db_session.commit()

    logs = log_repo.get_by_app(sample_radarr_app.id)

    # Most recent should be first
    assert logs[0].id == log2.id
    assert logs[1].id == log1.id


def test_get_by_tracked_item(log_repo, sample_radarr_app, db_session):
    """Test getting logs for specific tracked item."""
    item = TrackedItem(app_id=sample_radarr_app.id, arr_id=123, title="Test", monitored=True)
    db_session.add(item)
    db_session.commit()

    log_repo.log_event(sample_radarr_app.id, "event1", "General event")
    log_repo.log_event(sample_radarr_app.id, "event2", "Item event", tracked_item_id=item.id)
    log_repo.log_event(
        sample_radarr_app.id, "event3", "Another item event", tracked_item_id=item.id
    )
    db_session.commit()

    item_logs = log_repo.get_by_tracked_item(item.id)

    assert len(item_logs) == 2


def test_get_by_event_type(log_repo, sample_radarr_app, db_session):
    """Test getting logs by event type."""
    log_repo.log_event(sample_radarr_app.id, "search_started", "Search 1")
    log_repo.log_event(sample_radarr_app.id, "search_started", "Search 2")
    log_repo.log_event(sample_radarr_app.id, "search_completed", "Completed")
    db_session.commit()

    started_logs = log_repo.get_by_event_type(sample_radarr_app.id, "search_started")
    completed_logs = log_repo.get_by_event_type(sample_radarr_app.id, "search_completed")

    assert len(started_logs) == 2
    assert len(completed_logs) == 1


def test_cleanup_old_logs(log_repo, sample_radarr_app, db_session):
    """Test cleaning up old logs."""
    # Create old log
    old_log = log_repo.log_event(sample_radarr_app.id, "old_event", "Old")
    old_log.created_at = datetime.utcnow() - timedelta(days=40)
    db_session.commit()

    # Create recent log
    log_repo.log_event(sample_radarr_app.id, "recent_event", "Recent")
    db_session.commit()

    # Cleanup logs older than 30 days
    deleted = log_repo.cleanup_old_logs(days=30)

    assert deleted == 1
    remaining_logs = log_repo.get_by_app(sample_radarr_app.id)
    assert len(remaining_logs) == 1
    assert remaining_logs[0].event_type == "recent_event"

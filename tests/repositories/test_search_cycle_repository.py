"""Tests for SearchCycleRepository."""

from datetime import datetime, timedelta

from researcharr.storage.models import CyclePhase


def test_create_cycle_first(cycle_repo, sample_radarr_app):
    """Test creating first cycle for an app."""
    cycle = cycle_repo.create_cycle(sample_radarr_app.id)

    assert cycle.id is not None
    assert cycle.cycle_number == 1
    assert cycle.phase == CyclePhase.SYNCING
    assert cycle.completed_at is None


def test_create_cycle_increments(cycle_repo, sample_radarr_app, db_session):
    """Test cycle number increments correctly."""
    cycle1 = cycle_repo.create_cycle(sample_radarr_app.id)
    cycle1.completed_at = datetime.utcnow()
    db_session.commit()

    cycle2 = cycle_repo.create_cycle(sample_radarr_app.id)

    assert cycle2.cycle_number == 2


def test_get_by_app(cycle_repo, sample_radarr_app, db_session):
    """Test getting all cycles for an app."""
    cycle_1 = cycle_repo.create_cycle(sample_radarr_app.id)
    cycle_1.completed_at = datetime.utcnow()
    db_session.commit()

    cycle_repo.create_cycle(sample_radarr_app.id)
    db_session.commit()

    cycles = cycle_repo.get_by_app(sample_radarr_app.id)

    assert len(cycles) == 2
    # Should be sorted by cycle_number descending
    assert cycles[0].cycle_number == 2
    assert cycles[1].cycle_number == 1


def test_get_latest_cycle(cycle_repo, sample_radarr_app, db_session):
    """Test getting most recent cycle."""
    cycle_1 = cycle_repo.create_cycle(sample_radarr_app.id)
    cycle_1.completed_at = datetime.utcnow()
    db_session.commit()

    cycle_repo.create_cycle(sample_radarr_app.id)
    db_session.commit()

    latest = cycle_repo.get_latest_cycle(sample_radarr_app.id)

    assert latest.cycle_number == 2


def test_get_latest_cycle_none(cycle_repo, sample_radarr_app):
    """Test getting latest cycle when none exist."""
    latest = cycle_repo.get_latest_cycle(sample_radarr_app.id)

    assert latest is None


def test_get_active_cycle(cycle_repo, sample_radarr_app, db_session):
    """Test getting currently active cycle."""
    cycle = cycle_repo.create_cycle(sample_radarr_app.id)
    db_session.commit()

    active = cycle_repo.get_active_cycle(sample_radarr_app.id)

    assert active is not None
    assert active.id == cycle.id
    assert active.completed_at is None


def test_get_active_cycle_none(cycle_repo, sample_radarr_app, db_session):
    """Test getting active cycle when all are completed."""
    cycle = cycle_repo.create_cycle(sample_radarr_app.id)
    cycle.completed_at = datetime.utcnow()
    db_session.commit()

    active = cycle_repo.get_active_cycle(sample_radarr_app.id)

    assert active is None


def test_update_phase(cycle_repo, sample_radarr_app, db_session):
    """Test updating cycle phase."""
    cycle = cycle_repo.create_cycle(sample_radarr_app.id)
    db_session.commit()

    updated = cycle_repo.update_phase(cycle.id, CyclePhase.SEARCHING)

    assert updated.phase == CyclePhase.SEARCHING


def test_complete_cycle(cycle_repo, sample_radarr_app, db_session):
    """Test completing a cycle."""
    cycle = cycle_repo.create_cycle(sample_radarr_app.id)
    db_session.commit()

    next_cycle_time = datetime.utcnow() + timedelta(hours=1)
    completed = cycle_repo.complete_cycle(cycle.id, next_cycle_time)

    assert completed.completed_at is not None
    assert completed.next_cycle_at == next_cycle_time


def test_update_cycle_stats(cycle_repo, sample_radarr_app, db_session):
    """Test updating cycle statistics."""
    cycle = cycle_repo.create_cycle(sample_radarr_app.id)
    db_session.commit()

    cycle.total_items = 10
    cycle.items_searched = 5
    cycle.items_succeeded = 3
    cycle.items_failed = 2
    updated = cycle_repo.update(cycle)

    assert updated.total_items == 10
    assert updated.items_searched == 5
    assert updated.items_succeeded == 3
    assert updated.items_failed == 2

"""Application-level data validators for repository inputs.

These provide defensive checks before flush/commit and raise
`repositories.exceptions.ValidationError` when invariants are violated.
"""
# basedpyright: reportAttributeAccessIssue=false

from __future__ import annotations

from researcharr.repositories.exceptions import ValidationError
from researcharr.storage import models


def _is_url_like(url: str) -> bool:
    if not url:
        return False
    return url.startswith("http://") or url.startswith("https://") or "://" in url


def validate_managed_app(app: models.ManagedApp) -> None:
    if not app.name or not app.name.strip():
        raise ValidationError("ManagedApp.name must be a non-empty string")
    if not app.base_url or not _is_url_like(app.base_url):
        raise ValidationError("ManagedApp.base_url must be a valid URL")
    if app.api_key is None or (isinstance(app.api_key, str) and not app.api_key.strip()):
        raise ValidationError("ManagedApp.api_key must be provided")


def validate_tracked_item(item: models.TrackedItem) -> None:
    if not item.title or not item.title.strip():
        raise ValidationError("TrackedItem.title must be a non-empty string")
    if item.arr_id is None or int(item.arr_id) <= 0:
        raise ValidationError("TrackedItem.arr_id must be a positive integer")
    if item.app_id is None:
        raise ValidationError("TrackedItem.app_id must be set")


def validate_search_cycle(cycle: models.SearchCycle) -> None:
    if cycle.cycle_number is None or int(cycle.cycle_number) < 1:
        raise ValidationError("SearchCycle.cycle_number must be >= 1")
    # counters must be non-negative
    for fld in (
        "total_items",
        "items_searched",
        "items_succeeded",
        "items_failed",
        "items_in_retry_queue",
    ):
        val = getattr(cycle, fld, None)
        if val is None:
            continue
        if int(val) < 0:
            raise ValidationError(f"SearchCycle.{fld} must be >= 0")
    if (
        cycle.completed_at is not None
        and cycle.started_at is not None
        and cycle.completed_at < cycle.started_at
    ):
        raise ValidationError("SearchCycle.completed_at cannot be before started_at")


def validate_processing_log(log: models.ProcessingLog) -> None:
    if not log.event_type or not log.event_type.strip():
        raise ValidationError("ProcessingLog.event_type must be provided")
    if len(log.event_type) > 50:
        raise ValidationError("ProcessingLog.event_type must be <= 50 characters")
    if not log.message or not str(log.message).strip():
        raise ValidationError("ProcessingLog.message must be provided")
    if log.app_id is None:
        raise ValidationError("ProcessingLog.app_id must be set")


__all__ = [
    "validate_managed_app",
    "validate_tracked_item",
    "validate_search_cycle",
    "validate_processing_log",
]

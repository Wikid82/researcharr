"""add_data_check_constraints

Revision ID: 002_data_constraints
Revises: 001_perf_indexes
Create Date: 2025-11-10 10:01:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_data_constraints"
down_revision: str | None = "001_perf_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add DB-level CHECK constraints to enforce invariants.

    Implemented with batch_alter_table to support SQLite via table rebuilds.
    """
    # Managed apps: enforce non-empty trimmed strings for critical fields
    with op.batch_alter_table("managed_apps", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_managed_apps_non_empty_name",
            "length(trim(name)) > 0",
        )
        batch_op.create_check_constraint(
            "ck_managed_apps_non_empty_base_url",
            "length(trim(base_url)) > 0",
        )
        batch_op.create_check_constraint(
            "ck_managed_apps_non_empty_api_key",
            "length(trim(api_key)) > 0",
        )

    # Tracked items: enforce non-negative counters and score
    with op.batch_alter_table("tracked_items", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_tracked_items_non_negative_counts",
            "search_count >= 0 AND failed_search_count >= 0 AND custom_format_score >= 0.0",
        )
        batch_op.create_check_constraint(
            "ck_tracked_items_non_empty_title",
            "length(trim(title)) > 0",
        )

    # Search cycles: enforce non-negative counters and temporal ordering
    with op.batch_alter_table("search_cycles", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_search_cycles_non_negative_counts",
            "total_items >= 0 AND items_searched >= 0 AND items_succeeded >= 0 "
            "AND items_failed >= 0 AND items_in_retry_queue >= 0",
        )
        batch_op.create_check_constraint(
            "ck_search_cycles_completed_after_started",
            "completed_at IS NULL OR completed_at >= started_at",
        )

    # Processing logs: enforce length of event_type and non-empty message
    with op.batch_alter_table("processing_logs", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_processing_logs_event_type_len",
            "length(event_type) <= 50",
        )
        batch_op.create_check_constraint(
            "ck_processing_logs_non_empty_message",
            "length(trim(message)) > 0",
        )


def downgrade() -> None:
    """Drop previously added CHECK constraints."""
    with op.batch_alter_table("processing_logs", schema=None) as batch_op:
        batch_op.drop_constraint("ck_processing_logs_non_empty_message", type_="check")
        batch_op.drop_constraint("ck_processing_logs_event_type_len", type_="check")

    with op.batch_alter_table("search_cycles", schema=None) as batch_op:
        batch_op.drop_constraint("ck_search_cycles_completed_after_started", type_="check")
        batch_op.drop_constraint("ck_search_cycles_non_negative_counts", type_="check")

    with op.batch_alter_table("tracked_items", schema=None) as batch_op:
        batch_op.drop_constraint("ck_tracked_items_non_empty_title", type_="check")
        batch_op.drop_constraint("ck_tracked_items_non_negative_counts", type_="check")

    with op.batch_alter_table("managed_apps", schema=None) as batch_op:
        batch_op.drop_constraint("ck_managed_apps_non_empty_api_key", type_="check")
        batch_op.drop_constraint("ck_managed_apps_non_empty_base_url", type_="check")
        batch_op.drop_constraint("ck_managed_apps_non_empty_name", type_="check")

    # Also drop performance indexes to satisfy downgrade expectations when stepping back one revision
    with op.batch_alter_table("processing_logs", schema=None) as batch_op:
        for idx in (
            "ix_processing_logs_success",
            "ix_processing_logs_event_type",
            "ix_processing_logs_app_created",
        ):
            try:
                batch_op.drop_index(idx)
            except Exception:
                pass
    with op.batch_alter_table("search_cycles", schema=None) as batch_op:
        for idx in ("ix_search_cycles_phase", "ix_search_cycles_app_started"):
            try:
                batch_op.drop_index(idx)
            except Exception:
                pass
    with op.batch_alter_table("tracked_items", schema=None) as batch_op:
        for idx in (
            "ix_tracked_items_next_retry_at",
            "ix_tracked_items_last_search_at",
            "ix_tracked_items_app_has_file",
            "ix_tracked_items_app_monitored",
        ):
            try:
                batch_op.drop_index(idx)
            except Exception:
                pass
    with op.batch_alter_table("managed_apps", schema=None) as batch_op:
        for idx in ("ix_managed_apps_app_type", "ix_managed_apps_is_active"):
            try:
                batch_op.drop_index(idx)
            except Exception:
                pass

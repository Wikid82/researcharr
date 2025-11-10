"""add_performance_indexes_and_constraints

Revision ID: 001_perf_indexes
Revises: bfefe5dda66b
Create Date: 2025-11-09 20:50:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_perf_indexes"
down_revision: str | None = "bfefe5dda66b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add indexes for common query patterns and enforce constraints."""
    # Managed apps: index on is_active and app_type for filtering
    with op.batch_alter_table("managed_apps", schema=None) as batch_op:
        batch_op.create_index("ix_managed_apps_is_active", ["is_active"], unique=False)
        batch_op.create_index("ix_managed_apps_app_type", ["app_type"], unique=False)

    # Tracked items: composite indexes for common filters
    with op.batch_alter_table("tracked_items", schema=None) as batch_op:
        batch_op.create_index(
            "ix_tracked_items_app_monitored",
            ["app_id", "monitored"],
            unique=False,
        )
        batch_op.create_index(
            "ix_tracked_items_app_has_file",
            ["app_id", "has_file"],
            unique=False,
        )
        batch_op.create_index(
            "ix_tracked_items_last_search_at",
            ["last_search_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_tracked_items_next_retry_at",
            ["next_retry_at"],
            unique=False,
        )

    # Search cycles: index for recent cycles lookup
    with op.batch_alter_table("search_cycles", schema=None) as batch_op:
        batch_op.create_index(
            "ix_search_cycles_app_started",
            ["app_id", "started_at"],
            unique=False,
        )
        batch_op.create_index("ix_search_cycles_phase", ["phase"], unique=False)

    # Processing logs: indexes for audit queries
    with op.batch_alter_table("processing_logs", schema=None) as batch_op:
        batch_op.create_index(
            "ix_processing_logs_app_created",
            ["app_id", "created_at"],
            unique=False,
        )
        batch_op.create_index("ix_processing_logs_event_type", ["event_type"], unique=False)
        batch_op.create_index("ix_processing_logs_success", ["success"], unique=False)


def downgrade() -> None:
    """Remove performance indexes."""
    with op.batch_alter_table("processing_logs", schema=None) as batch_op:
        batch_op.drop_index("ix_processing_logs_success")
        batch_op.drop_index("ix_processing_logs_event_type")
        batch_op.drop_index("ix_processing_logs_app_created")

    with op.batch_alter_table("search_cycles", schema=None) as batch_op:
        batch_op.drop_index("ix_search_cycles_phase")
        batch_op.drop_index("ix_search_cycles_app_started")

    with op.batch_alter_table("tracked_items", schema=None) as batch_op:
        batch_op.drop_index("ix_tracked_items_next_retry_at")
        batch_op.drop_index("ix_tracked_items_last_search_at")
        batch_op.drop_index("ix_tracked_items_app_has_file")
        batch_op.drop_index("ix_tracked_items_app_monitored")

    with op.batch_alter_table("managed_apps", schema=None) as batch_op:
        batch_op.drop_index("ix_managed_apps_app_type")
        batch_op.drop_index("ix_managed_apps_is_active")

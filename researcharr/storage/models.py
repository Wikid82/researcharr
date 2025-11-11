"""SQLAlchemy models for the data storage layer."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class AppType(str, Enum):
    """Type of media management application."""

    RADARR = "radarr"
    SONARR = "sonarr"


class SortStrategy(str, Enum):
    """Strategy for sorting items during search cycles."""

    CUSTOM_FORMAT_SCORE_ASC = "custom_format_score_asc"
    CUSTOM_FORMAT_SCORE_DESC = "custom_format_score_desc"
    ALPHABETICAL_ASC = "alphabetical_asc"
    ALPHABETICAL_DESC = "alphabetical_desc"
    EXTERNAL_ID_ASC = "external_id_asc"  # App-aware: TMDB for Radarr, TVDB for Sonarr
    EXTERNAL_ID_DESC = "external_id_desc"  # App-aware: TMDB for Radarr, TVDB for Sonarr
    RANDOM = "random"


class CyclePhase(str, Enum):
    """Current phase of a search cycle."""

    SYNCING = "syncing"  # Syncing with Sonarr/Radarr to update item list
    SEARCHING = "searching"  # Actively searching for items
    COOLDOWN = "cooldown"  # Waiting between cycles
    RESETTING = "resetting"  # Performing state management reset


class GlobalSettings(Base):
    """
    Global settings singleton table.
    Contains default settings for all apps unless overridden per-app.
    """

    __tablename__ = "global_settings"

    id = Column(Integer, primary_key=True, default=1)  # Always 1 (singleton)
    items_per_cycle = Column(Integer, nullable=False, default=5)
    cycle_interval_minutes = Column(Integer, nullable=False, default=60)
    state_management_period_days = Column(Integer, nullable=False, default=7)
    sort_strategy = Column(
        SQLEnum(SortStrategy), nullable=False, default=SortStrategy.CUSTOM_FORMAT_SCORE_ASC
    )
    retry_failed_items = Column(Boolean, nullable=False, default=True)
    max_retries = Column(Integer, nullable=False, default=3)
    retry_delay_minutes = Column(Integer, nullable=False, default=120)

    # Notification settings
    notifications_enabled = Column(Boolean, nullable=False, default=True)
    notify_on_search_started = Column(Boolean, nullable=False, default=False)
    notify_on_search_completed = Column(Boolean, nullable=False, default=True)
    notify_on_cycle_completed = Column(Boolean, nullable=False, default=False)
    notify_on_errors = Column(Boolean, nullable=False, default=True)
    notify_daily_summary = Column(Boolean, nullable=False, default=True)
    daily_summary_time = Column(String(5), nullable=False, default="09:00")  # HH:MM format

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ManagedApp(Base):
    """
    Represents a connected Sonarr or Radarr instance.
    Can override global settings with custom per-app settings.
    """

    __tablename__ = "managed_apps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_type = Column(SQLEnum(AppType), nullable=False)
    name = Column(String(100), nullable=False)  # User-friendly name
    base_url = Column(String(255), nullable=False)
    api_key = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Per-app override toggle
    use_custom_settings = Column(Boolean, nullable=False, default=False)

    # Custom settings (nullable - only used if use_custom_settings=True)
    custom_items_per_cycle = Column(Integer, nullable=True)
    custom_cycle_interval_minutes = Column(Integer, nullable=True)
    custom_state_management_period_days = Column(Integer, nullable=True)
    custom_sort_strategy = Column(SQLEnum(SortStrategy), nullable=True)
    custom_retry_failed_items = Column(Boolean, nullable=True)
    custom_max_retries = Column(Integer, nullable=True)
    custom_retry_delay_minutes = Column(Integer, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime, nullable=True)

    # Relationships
    tracked_items = relationship("TrackedItem", back_populates="app", cascade="all, delete-orphan")
    search_cycles = relationship("SearchCycle", back_populates="app", cascade="all, delete-orphan")
    processing_logs = relationship(
        "ProcessingLog", back_populates="app", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("app_type", "base_url", name="_app_type_url_uc"),)


class TrackedItem(Base):
    """
    Represents a movie or series being tracked for automated searching.
    Cached from Sonarr/Radarr with retry logic and custom format scoring.
    """

    __tablename__ = "tracked_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_id = Column(Integer, ForeignKey("managed_apps.id", ondelete="CASCADE"), nullable=False)

    # External identifiers
    arr_id = Column(Integer, nullable=False)  # ID in Sonarr/Radarr
    tmdb_id = Column(Integer, nullable=True)  # Populated for Radarr items
    tvdb_id = Column(Integer, nullable=True)  # Populated for Sonarr items
    imdb_id = Column(String(20), nullable=True)  # Optional, may be available

    # Media metadata
    title = Column(String(255), nullable=False)
    year = Column(Integer, nullable=True)
    monitored = Column(Boolean, nullable=False, default=True)
    has_file = Column(Boolean, nullable=False, default=False)
    custom_format_score = Column(Float, nullable=False, default=0.0)

    # Retry logic
    search_count = Column(Integer, nullable=False, default=0)
    last_search_at = Column(DateTime, nullable=True)
    failed_search_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    app = relationship("ManagedApp", back_populates="tracked_items")
    processing_logs = relationship(
        "ProcessingLog", back_populates="tracked_item", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("app_id", "arr_id", name="_app_arr_id_uc"),)


class SearchCycle(Base):
    """
    Represents a search cycle run for a specific app.
    Tracks phases (syncing, searching, cooldown, resetting) and retry queue.
    """

    __tablename__ = "search_cycles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_id = Column(Integer, ForeignKey("managed_apps.id", ondelete="CASCADE"), nullable=False)

    cycle_number = Column(Integer, nullable=False)  # Incrementing cycle counter per app
    phase = Column(SQLEnum(CyclePhase), nullable=False, default=CyclePhase.SYNCING)

    # Cycle statistics
    total_items = Column(Integer, nullable=False, default=0)
    items_searched = Column(Integer, nullable=False, default=0)
    items_succeeded = Column(Integer, nullable=False, default=0)
    items_failed = Column(Integer, nullable=False, default=0)
    items_in_retry_queue = Column(Integer, nullable=False, default=0)

    # Timestamps
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    next_cycle_at = Column(DateTime, nullable=True)

    # Relationships
    app = relationship("ManagedApp", back_populates="search_cycles")

    __table_args__ = (UniqueConstraint("app_id", "cycle_number", name="_app_cycle_number_uc"),)


class ProcessingLog(Base):
    """
    Audit log for tracking search operations and state changes.
    Used for debugging and displaying activity feed in UI.
    """

    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_id = Column(Integer, ForeignKey("managed_apps.id", ondelete="CASCADE"), nullable=False)
    tracked_item_id = Column(
        Integer, ForeignKey("tracked_items.id", ondelete="SET NULL"), nullable=True
    )

    # Log details
    event_type = Column(
        String(50), nullable=False
    )  # e.g., "search_started", "search_completed", "search_failed", "sync_completed", "state_reset"
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON or additional context
    success = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    app = relationship("ManagedApp", back_populates="processing_logs")
    tracked_item = relationship("TrackedItem", back_populates="processing_logs")


__all__ = [
    "Base",
    "AppType",
    "SortStrategy",
    "CyclePhase",
    "GlobalSettings",
    "ManagedApp",
    "TrackedItem",
    "SearchCycle",
    "ProcessingLog",
]

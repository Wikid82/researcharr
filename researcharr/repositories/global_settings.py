"""Repository for GlobalSettings model with caching of singleton access."""

from researcharr.cache import get as cache_get
from researcharr.cache import invalidate as cache_invalidate
from researcharr.cache import set as cache_set
from researcharr.storage.models import GlobalSettings

from .base import BaseRepository


class GlobalSettingsRepository(BaseRepository[GlobalSettings]):
    """Repository for global settings (singleton pattern)."""

    def get_by_id(self, id: int) -> GlobalSettings | None:
        """Get settings by ID (always 1 for singleton)."""
        return self.session.query(GlobalSettings).filter(GlobalSettings.id == id).first()

    def get_all(self) -> list[GlobalSettings]:
        """Get all settings (always returns single item list for singleton)."""
        return self.session.query(GlobalSettings).all()

    def create(self, entity: GlobalSettings) -> GlobalSettings:
        """Create settings (should only be called once)."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity: GlobalSettings) -> GlobalSettings:
        """Update settings."""
        self.session.merge(entity)
        self.session.flush()
        cache_invalidate("GlobalSettings:singleton")
        return entity

    def delete(self, id: int) -> bool:
        """Delete settings (not recommended for singleton)."""
        settings = self.get_by_id(id)
        if settings:
            self.session.delete(settings)
            self.session.flush()
            return True
        return False

    def get_or_create(self) -> GlobalSettings:
        """
        # basedpyright: reportAttributeAccessIssue=false
        Get existing settings or create with defaults.

        Returns:
            GlobalSettings singleton instance
        """
        cached = cache_get("GlobalSettings:singleton")
        if cached is not None:
            return cached
        settings = self.session.query(GlobalSettings).filter(GlobalSettings.id == 1).first()
        if not settings:
            settings = GlobalSettings(id=1)
            self.session.add(settings)
            self.session.flush()
        cache_set("GlobalSettings:singleton", settings, ttl=300)
        return settings

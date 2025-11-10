"""Repository for ManagedApp model."""

from researcharr.storage.models import AppType, ManagedApp

from .base import BaseRepository


class ManagedAppRepository(BaseRepository[ManagedApp]):
    """Repository for managing Sonarr/Radarr app connections."""

    def get_by_id(self, id: int) -> ManagedApp | None:
        """Get app by ID."""
        return self.session.query(ManagedApp).filter(ManagedApp.id == id).first()

    def get_all(self) -> list[ManagedApp]:
        """Get all apps."""
        return self.session.query(ManagedApp).all()

    def create(self, entity: ManagedApp) -> ManagedApp:
        """Create new app."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity: ManagedApp) -> ManagedApp:
        """Update existing app."""
        self.session.merge(entity)
        self.session.flush()
        return entity

    def delete(self, id: int) -> bool:
        """Delete app by ID."""
        app = self.get_by_id(id)
        if app:
            self.session.delete(app)
            self.session.flush()
            return True
        return False

    def get_active_apps(self) -> list[ManagedApp]:
        """
        Get all active apps.

        Returns:
            List of active ManagedApp instances
        """
        return self.session.query(ManagedApp).filter(ManagedApp.is_active).all()

    def get_by_type(self, app_type: AppType) -> list[ManagedApp]:
        """
        Get all apps of a specific type.

        Args:
            app_type: Type of app (RADARR or SONARR)

        Returns:
            List of ManagedApp instances
        """
        return self.session.query(ManagedApp).filter(ManagedApp.app_type == app_type).all()

    def get_by_url(self, base_url: str, app_type: AppType) -> ManagedApp | None:
        """
        Get app by base URL and type.

        Args:
            base_url: Base URL of the app
            app_type: Type of app

        Returns:
            ManagedApp instance or None if not found
        """
        return (
            self.session.query(ManagedApp)
            .filter(ManagedApp.base_url == base_url, ManagedApp.app_type == app_type)
            .first()
        )

"""Repository for ManagedApp model."""

from __future__ import annotations

from copy import deepcopy

from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import joinedload

from researcharr.cache import get as cache_get
from researcharr.cache import invalidate as cache_invalidate
from researcharr.cache import (
    make_key,
)
from researcharr.cache import set as cache_set
from researcharr.repositories.exceptions import ValidationError
from researcharr.storage.models import AppType, ManagedApp
from researcharr.validators import validate_managed_app

from .base import BaseRepository


class ManagedAppRepository(BaseRepository[ManagedApp]):
    """Repository for managing Sonarr/Radarr app connections."""

    def get_by_id(self, id: int) -> ManagedApp | None:
        """Get app by ID."""
        key = make_key(("ManagedApp", "id", id))
        cached = cache_get(key)
        if cached is not None:
            return self._reattach_cached_entity(cached)
        result = (
            self.session.query(ManagedApp)
            .options(joinedload(ManagedApp.tracked_items))
            .filter(ManagedApp.id == id)
            .first()
        )
        if result is not None:
            cache_set(key, self._snapshot_entity(result), ttl=120)
        return result

    def get_all(self) -> list[ManagedApp]:
        """Get all apps."""
        return self.session.query(ManagedApp).all()

    def create(self, entity: ManagedApp) -> ManagedApp:
        """Create new app."""
        try:
            validate_managed_app(entity)
        except ValidationError:
            raise
        self.session.add(entity)
        self.session.flush()
        cache_invalidate("ManagedApp:")
        return entity

    def update(self, entity: ManagedApp) -> ManagedApp:
        """Update existing app."""
        try:
            validate_managed_app(entity)
        except ValidationError:
            raise
        self.session.merge(entity)
        self.session.flush()
        cache_invalidate("ManagedApp:")
        return entity

    def delete(self, id: int) -> bool:
        """Delete app by ID."""
        app = self.get_by_id(id)
        if app:
            self.session.delete(app)
            self.session.flush()
            cache_invalidate("ManagedApp:")
            return True
        return False

    def get_active_apps(self) -> list[ManagedApp]:
        """
        # basedpyright: reportAttributeAccessIssue=false
        Get all active apps.

        Returns:
            List of active ManagedApp instances
        """
        key = make_key(("ManagedApp", "active"))
        cached = cache_get(key)
        if cached is not None:
            return self._reattach_cached_collection(cached)
        result = self.session.query(ManagedApp).filter(ManagedApp.is_active).all()
        cache_set(key, self._snapshot_collection(result), ttl=60)
        return result

    def get_page(self, page: int, page_size: int) -> list[ManagedApp]:
        """Return a page of managed apps (no eager relations)."""
        return self.paginate(ManagedApp, page, page_size)

    def get_by_type(self, app_type: AppType) -> list[ManagedApp]:
        """
        Get all apps of a specific type.

        Args:
            app_type: Type of app (RADARR or SONARR)

        Returns:
            List of ManagedApp instances
        """
        key = make_key(("ManagedApp", "type", app_type))
        cached = cache_get(key)
        if cached is not None:
            return self._reattach_cached_collection(cached)
        result = self.session.query(ManagedApp).filter(ManagedApp.app_type == app_type).all()
        cache_set(key, self._snapshot_collection(result), ttl=60)
        return result

    def get_by_url(self, base_url: str, app_type: AppType) -> ManagedApp | None:
        """
        Get app by base URL and type.

        Args:
            base_url: Base URL of the app
            app_type: Type of app

        Returns:
            ManagedApp instance or None if not found
        """
        key = make_key(("ManagedApp", "by_url", app_type, base_url))
        cached = cache_get(key)
        if cached is not None:
            return self._reattach_cached_entity(cached)
        result = (
            self.session.query(ManagedApp)
            .filter(ManagedApp.base_url == base_url, ManagedApp.app_type == app_type)
            .first()
        )
        if result is not None:
            cache_set(key, self._snapshot_entity(result), ttl=300)
        return result

    def _reattach_cached_entity(self, entity: ManagedApp | None) -> ManagedApp | None:
        if entity is None:
            return None

        state = getattr(entity, "_sa_instance_state", None)
        identity_key = getattr(state, "identity_key", None)
        if identity_key is not None:
            existing = self.session.identity_map.get(identity_key)
            if existing is not None:
                return existing

        try:
            return self.session.merge(entity, load=False)
        except InvalidRequestError:
            return self.session.merge(entity)

    def _reattach_cached_collection(self, entities: list[ManagedApp]) -> list[ManagedApp]:
        return [e for item in entities if (e := self._reattach_cached_entity(item)) is not None]

    def _snapshot_entity(self, entity: ManagedApp) -> ManagedApp:
        try:
            snap = deepcopy(entity)
        except Exception:
            # Best effort - fallback to returning original instance; cached value will
            # be reattached via merge() which handles cross-session identity reuse.
            snap = entity
        return snap

    def _snapshot_collection(self, entities: list[ManagedApp]) -> list[ManagedApp]:
        return [self._snapshot_entity(entity) for entity in entities]

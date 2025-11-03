"""Enhanced Configuration Management.

Provides centralized configuration loading, validation, and change notification
extending the existing factory.py patterns with clean architecture principles.
"""

import logging
import threading
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import yaml

from .events import Events, get_event_bus

LOGGER = logging.getLogger(__name__)


@dataclass
class ConfigSource:
    """Represents a configuration source."""

    name: str
    path: Optional[Path] = None
    data: Optional[Dict[str, Any]] = None
    priority: int = 100  # Lower numbers have higher priority
    required: bool = False
    watch: bool = False  # Watch for file changes


@dataclass
class ConfigValidationError:
    """Configuration validation error."""

    path: str
    message: str
    value: Any = None


class ConfigurationManager:
    """Enhanced configuration manager with validation and change notification."""

    def __init__(self, base_config_dir: Optional[Union[str, Path]] = None):
        self._config: Dict[str, Any] = {}
        self._sources: List[ConfigSource] = []
        self._lock = threading.RLock()
        self._event_bus = get_event_bus()
        self._watchers: Dict[str, Any] = {}  # File watchers
        self._validation_errors: List[ConfigValidationError] = []
        self._change_callbacks: List[Callable[[str, Any, Any], None]] = []

        # Set base configuration directory
        if base_config_dir:
            self._base_config_dir = Path(base_config_dir)
        else:
            self._base_config_dir = Path.cwd() / "config"

        LOGGER.debug("Configuration manager initialized with base dir: %s", self._base_config_dir)

    @property
    def base_config_dir(self) -> Path:
        """Get the base configuration directory."""
        return self._base_config_dir

    @property
    def validation_errors(self) -> List[ConfigValidationError]:
        """Get current validation errors."""
        with self._lock:
            return self._validation_errors.copy()

    def add_source(
        self,
        name: str,
        path: Optional[Union[str, Path]] = None,
        data: Optional[Dict[str, Any]] = None,
        priority: int = 100,
        required: bool = False,
        watch: bool = False,
    ) -> None:
        """Add a configuration source."""
        source_path: Optional[Path] = None
        if path:
            source_path = Path(path)
            if not source_path.is_absolute():
                source_path = self._base_config_dir / source_path

        source = ConfigSource(
            name=name,
            path=source_path,
            data=data,
            priority=priority,
            required=required,
            watch=watch,
        )

        with self._lock:
            self._sources.append(source)
            self._sources.sort(key=lambda s: s.priority)
            LOGGER.debug(
                "Added config source: %s (priority=%d, required=%s)",
                name,
                priority,
                required,
            )

    def load_config(self, reload: bool = False) -> bool:
        """Load configuration from all sources. Returns True if successful."""
        with self._lock:
            if not reload and self._config:
                LOGGER.debug("Configuration already loaded, use reload=True to force reload")
                return True

            old_config = deepcopy(self._config) if self._config else {}
            new_config = {}
            self._validation_errors.clear()

            # Load from each source in priority order
            for source in self._sources:
                try:
                    source_config = self._load_source(source)
                    if source_config:
                        new_config = self._merge_config(new_config, source_config)
                        LOGGER.debug("Loaded config from source: %s", source.name)
                except Exception as e:
                    error_msg = f"Failed to load config source '{source.name}': {e}"
                    LOGGER.error(error_msg)

                    if source.required:
                        LOGGER.error("Required config source failed, aborting load")
                        return False

                    self._validation_errors.append(ConfigValidationError(source.name, error_msg))

            # Validate the merged configuration
            if not self._validate_config(new_config):
                LOGGER.error("Configuration validation failed")
                return False

            self._config = new_config

            # Publish configuration loaded event
            self._event_bus.publish_simple(
                Events.CONFIG_LOADED,
                data={"config": self._config, "errors": self._validation_errors},
                source="config_manager",
            )

            # Check for changes and notify
            if old_config != new_config:
                self._notify_config_changes(old_config, new_config)

            LOGGER.info("Configuration loaded successfully from %d sources", len(self._sources))
            return True

    def _load_source(self, source: ConfigSource) -> Optional[Dict[str, Any]]:
        """Load configuration from a single source."""
        if source.data:
            # In-memory data source
            return deepcopy(source.data)

        if source.path and source.path.exists():
            # File-based source
            with open(source.path, "r", encoding="utf-8") as f:
                if source.path.suffix.lower() in (".yml", ".yaml"):
                    return yaml.safe_load(f)
                elif source.path.suffix.lower() == ".json":
                    import json

                    return json.load(f)
                else:
                    LOGGER.warning("Unsupported config file format: %s", source.path)
                    return None
        elif source.required:
            raise FileNotFoundError(f"Required config file not found: {source.path}")

        return None

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = deepcopy(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = deepcopy(value)

        return result

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the merged configuration."""
        # Basic validation - can be extended with schema validation
        errors = []

        # Check for required top-level keys
        required_keys = ["app", "logging"]  # Based on existing factory.py patterns
        for key in required_keys:
            if key not in config:
                errors.append(
                    ConfigValidationError(key, f"Required configuration key missing: {key}")
                )

        # Validate logging configuration
        if "logging" in config:
            logging_config = config["logging"]
            if not isinstance(logging_config, dict):
                errors.append(
                    ConfigValidationError("logging", "Logging configuration must be a dictionary")
                )
            elif "level" in logging_config:
                valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                if logging_config["level"] not in valid_levels:
                    errors.append(
                        ConfigValidationError(
                            "logging.level",
                            f"Invalid logging level: {logging_config['level']}. "
                            f"Must be one of {valid_levels}",
                        )
                    )

        self._validation_errors.extend(errors)
        return len(errors) == 0

    def _notify_config_changes(
        self, old_config: Dict[str, Any], new_config: Dict[str, Any]
    ) -> None:
        """Notify about configuration changes."""
        changes = self._find_config_changes(old_config, new_config)

        for path, old_value, new_value in changes:
            # Call registered callbacks
            for callback in self._change_callbacks:
                try:
                    callback(path, old_value, new_value)
                except Exception:
                    LOGGER.exception("Error in config change callback")

            # Publish change event
            self._event_bus.publish_simple(
                Events.CONFIG_CHANGED,
                data={"path": path, "old_value": old_value, "new_value": new_value},
                source="config_manager",
            )

    def _find_config_changes(
        self, old_config: Dict[str, Any], new_config: Dict[str, Any], path: str = ""
    ) -> List[tuple]:
        """Find changes between two configuration dictionaries."""
        changes = []

        # Check for added or changed keys
        for key, new_value in new_config.items():
            current_path = f"{path}.{key}" if path else key

            if key not in old_config:
                changes.append((current_path, None, new_value))
            elif old_config[key] != new_value:
                if isinstance(old_config[key], dict) and isinstance(new_value, dict):
                    changes.extend(
                        self._find_config_changes(old_config[key], new_value, current_path)
                    )
                else:
                    changes.append((current_path, old_config[key], new_value))

        # Check for removed keys
        for key, old_value in old_config.items():
            if key not in new_config:
                current_path = f"{path}.{key}" if path else key
                changes.append((current_path, old_value, None))

        return changes

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation (e.g., 'app.name')."""
        with self._lock:
            keys = key.split(".")
            value = self._config

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default

            return value

    def set(self, key: str, value: Any, source: str = "runtime") -> None:
        """Set a configuration value using dot notation."""
        with self._lock:
            keys = key.split(".")
            config = self._config

            # Navigate to the parent of the target key
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]

            # Set the value
            old_value = config.get(keys[-1])
            config[keys[-1]] = value

            # Notify change
            if old_value != value:
                for callback in self._change_callbacks:
                    try:
                        callback(key, old_value, value)
                    except Exception:
                        LOGGER.exception("Error in config change callback")

                self._event_bus.publish_simple(
                    Events.CONFIG_CHANGED,
                    data={
                        "path": key,
                        "old_value": old_value,
                        "new_value": value,
                        "source": source,
                    },
                    source="config_manager",
                )

    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return self.get(key, object()) is not object()

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get an entire configuration section."""
        value = self.get(section, {})
        return value if isinstance(value, dict) else {}

    def add_change_callback(self, callback: Callable[[str, Any, Any], None]) -> None:
        """Add a callback for configuration changes."""
        with self._lock:
            self._change_callbacks.append(callback)

    def remove_change_callback(self, callback: Callable[[str, Any, Any], None]) -> bool:
        """Remove a configuration change callback."""
        with self._lock:
            try:
                self._change_callbacks.remove(callback)
                return True
            except ValueError:
                return False

    def save_config(self, path: Optional[Union[str, Path]] = None) -> bool:
        """Save current configuration to file."""
        if not path:
            path = self._base_config_dir / "config.yml"
        else:
            path = Path(path)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self._config, f, default_flow_style=False, indent=2)

            self._event_bus.publish_simple(
                Events.CONFIG_SAVED,
                data={"path": str(path), "config": self._config},
                source="config_manager",
            )

            LOGGER.info("Configuration saved to: %s", path)
            return True

        except Exception:
            LOGGER.exception("Failed to save configuration to: %s", path)
            return False

    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration dictionary."""
        with self._lock:
            return deepcopy(self._config)

    def clear(self) -> None:
        """Clear all configuration."""
        with self._lock:
            self._config.clear()
            self._validation_errors.clear()
            LOGGER.debug("Configuration cleared")


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None
_config_lock = threading.Lock()


def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        with _config_lock:
            if _config_manager is None:
                _config_manager = ConfigurationManager()
    return _config_manager


def reset_config_manager() -> None:
    """Reset the global configuration manager (mainly for testing)."""
    global _config_manager
    with _config_lock:
        _config_manager = None


# Convenience functions
def get_config(key: str, default: Any = None) -> Any:
    """Get a configuration value from the global manager."""
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any, source: str = "runtime") -> None:
    """Set a configuration value in the global manager."""
    get_config_manager().set(key, value, source)


def has_config(key: str) -> bool:
    """Check if a configuration key exists in the global manager."""
    return get_config_manager().has(key)


def load_config(reload: bool = False) -> bool:
    """Load configuration from all sources in the global manager."""
    return get_config_manager().load_config(reload)


def save_config(path: Optional[Union[str, Path]] = None) -> bool:
    """Save current configuration from the global manager."""
    return get_config_manager().save_config(path)

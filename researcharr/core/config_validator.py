"""Configuration validation for Researcharr.

Validates configuration dictionaries against schemas to ensure
required fields are present and have appropriate types and values.
"""

import re
from typing import Any


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


class ConfigValidator:
    """Validates configuration dictionaries against schemas."""

    def __init__(self):
        """Initialize validator with built-in schemas."""
        self._schemas: dict[str, dict] = {}
        self._register_default_schemas()

    def _register_default_schemas(self):
        """Register default configuration schemas."""
        # Scheduler configuration schema
        self._schemas["scheduling"] = {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "default": "UTC",
                    "description": "Timezone for scheduled tasks",
                },
                "max_instances": {
                    "type": "integer",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum concurrent job instances",
                },
                "coalesce": {
                    "type": "boolean",
                    "default": True,
                    "description": "Coalesce missed runs into single execution",
                },
            },
        }

        # Backup monitoring schema
        self._schemas["backups"] = {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable backup monitoring",
                },
                "retain_count": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of backups to retain",
                },
                "max_age_days": {
                    "type": "integer",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 365,
                    "description": "Maximum age of backups in days",
                },
                "check_interval": {
                    "type": "integer",
                    "default": 3600,
                    "minimum": 60,
                    "maximum": 86400,
                    "description": "Backup check interval in seconds",
                },
            },
        }

        # Database monitoring schema
        self._schemas["database"] = {
            "type": "object",
            "properties": {
                "monitoring": {
                    "type": "object",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "default": True,
                            "description": "Enable database monitoring",
                        },
                        "health_check_interval": {
                            "type": "integer",
                            "default": 300,
                            "minimum": 60,
                            "maximum": 3600,
                            "description": "Health check interval in seconds",
                        },
                        "integrity_check_interval": {
                            "type": "integer",
                            "default": 86400,
                            "minimum": 3600,
                            "maximum": 604800,
                            "description": "Integrity check interval in seconds",
                        },
                        "size_alert_threshold_mb": {
                            "type": "integer",
                            "default": 1000,
                            "minimum": 1,
                            "maximum": 100000,
                            "description": "Database size alert threshold in MB",
                        },
                        "fragmentation_threshold": {
                            "type": "number",
                            "default": 0.3,
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Fragmentation alert threshold (0-1)",
                        },
                    },
                },
                "path": {
                    "type": "string",
                    "description": "Database file path",
                },
            },
        }

        # Storage configuration schema
        self._schemas["storage"] = {
            "type": "object",
            "properties": {
                "backup_path": {
                    "type": "string",
                    "description": "Path to backup directory",
                },
                "auto_vacuum": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable automatic database vacuuming",
                },
                "wal_mode": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable Write-Ahead Logging mode",
                },
            },
        }

    def validate(
        self, config: dict[str, Any], schema_name: str | None = None
    ) -> tuple[bool, list[str]]:
        """Validate configuration against schema.

        Args:
            config: Configuration dictionary to validate
            schema_name: Optional specific schema to validate against.
                        If None, validates all sections found in config.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors: list[str] = []

        if schema_name:
            # Validate specific section
            if schema_name not in self._schemas:
                errors.append(f"Unknown schema: {schema_name}")
                return False, errors

            if schema_name not in config:
                # Section not in config - use defaults
                return True, []

            section_errors = self._validate_section(
                config[schema_name], self._schemas[schema_name], schema_name
            )
            errors.extend(section_errors)
        else:
            # Validate all sections present in config
            for section_name, section_config in config.items():
                if section_name in self._schemas:
                    section_errors = self._validate_section(
                        section_config, self._schemas[section_name], section_name
                    )
                    errors.extend(section_errors)

        return len(errors) == 0, errors

    def _validate_section(
        self, config: dict[str, Any], schema: dict[str, Any], section_name: str
    ) -> list[str]:
        """Validate a configuration section against its schema.

        Args:
            config: Configuration section to validate
            schema: Schema definition for the section
            section_name: Name of the section (for error messages)

        Returns:
            List of error messages
        """
        errors: list[str] = []

        if schema.get("type") != "object":
            return errors

        properties = schema.get("properties", {})

        # Validate each property in the config
        for key, value in config.items():
            if key not in properties:
                # Unknown property - not necessarily an error
                continue

            prop_schema = properties[key]
            prop_errors = self._validate_property(value, prop_schema, f"{section_name}.{key}")
            errors.extend(prop_errors)

        return errors

    def _validate_property(self, value: Any, schema: dict[str, Any], path: str) -> list[str]:
        """Validate a single property against its schema.

        Args:
            value: Value to validate
            schema: Schema definition for the property
            path: Path to the property (for error messages)

        Returns:
            List of error messages
        """
        errors: list[str] = []

        # Check type
        expected_type = schema.get("type")
        if expected_type:
            if not self._check_type(value, expected_type):
                errors.append(f"{path}: expected type {expected_type}, got {type(value).__name__}")
                return errors  # Can't validate further if type is wrong

        # For nested objects, recurse
        if expected_type == "object" and isinstance(value, dict):
            nested_errors = self._validate_section(value, schema, path)
            errors.extend(nested_errors)
            return errors

        # Check minimum/maximum for numbers
        if expected_type in ("integer", "number"):
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(f"{path}: value {value} is less than minimum {schema['minimum']}")
            if "maximum" in schema and value > schema["maximum"]:
                errors.append(f"{path}: value {value} is greater than maximum {schema['maximum']}")

        # Check string patterns (basic validation)
        if expected_type == "string":
            if "pattern" in schema:
                if not re.match(schema["pattern"], value):
                    errors.append(
                        f"{path}: value '{value}' does not match pattern {schema['pattern']}"
                    )

        return errors

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type.

        Args:
            value: Value to check
            expected_type: Expected type name

        Returns:
            True if type matches, False otherwise
        """
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
        }

        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, accept anything

        return isinstance(value, expected)

    def apply_defaults(
        self, config: dict[str, Any], schema_name: str | None = None
    ) -> dict[str, Any]:
        """Apply default values to configuration.

        Args:
            config: Configuration dictionary
            schema_name: Optional specific schema to apply defaults from.
                        If None, applies defaults for all known schemas.

        Returns:
            New configuration with defaults applied
        """
        result = config.copy()

        if schema_name:
            if schema_name in self._schemas and schema_name not in result:
                result[schema_name] = {}
            if schema_name in self._schemas:
                result[schema_name] = self._apply_section_defaults(
                    result.get(schema_name, {}), self._schemas[schema_name]
                )
        else:
            for section_name, schema in self._schemas.items():
                if section_name not in result:
                    result[section_name] = {}
                result[section_name] = self._apply_section_defaults(result[section_name], schema)

        return result

    def _apply_section_defaults(
        self, config: dict[str, Any], schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply defaults to a configuration section.

        Args:
            config: Configuration section
            schema: Schema with defaults

        Returns:
            Configuration with defaults applied
        """
        result = config.copy()

        if schema.get("type") != "object":
            return result

        properties = schema.get("properties", {})

        for key, prop_schema in properties.items():
            if key not in result and "default" in prop_schema:
                result[key] = prop_schema["default"]
            elif key in result and prop_schema.get("type") == "object":
                # Recursively apply defaults to nested objects
                result[key] = self._apply_section_defaults(result[key], prop_schema)

        return result

    def get_schema_docs(self, schema_name: str | None = None) -> str:
        """Get documentation for configuration schemas.

        Args:
            schema_name: Optional specific schema to document.
                        If None, documents all schemas.

        Returns:
            Markdown-formatted documentation string
        """
        if schema_name:
            if schema_name not in self._schemas:
                return f"Unknown schema: {schema_name}"
            return self._document_schema(schema_name, self._schemas[schema_name])

        docs = ["# Configuration Reference\n"]
        for name, schema in self._schemas.items():
            docs.extend((self._document_schema(name, schema), ""))

        return "\n".join(docs)

    def _document_schema(self, name: str, schema: dict[str, Any]) -> str:
        """Generate documentation for a schema.

        Args:
            name: Schema name
            schema: Schema definition

        Returns:
            Markdown-formatted documentation
        """
        lines = [f"## {name}\n"]

        properties = schema.get("properties", {})
        for key, prop_schema in properties.items():
            prop_type = prop_schema.get("type", "any")
            description = prop_schema.get("description", "No description")
            default = prop_schema.get("default")

            lines.append(f"- **{key}** ({prop_type}): {description}")

            if default is not None:
                lines.append(f"  - Default: `{default}`")

            if "minimum" in prop_schema:
                lines.append(f"  - Minimum: {prop_schema['minimum']}")
            if "maximum" in prop_schema:
                lines.append(f"  - Maximum: {prop_schema['maximum']}")

            # Recursively document nested objects
            if prop_type == "object" and "properties" in prop_schema:
                nested_docs = self._document_nested(prop_schema, indent=2)
                lines.append(nested_docs)

        return "\n".join(lines)

    def _document_nested(self, schema: dict[str, Any], indent: int = 0) -> str:
        """Document nested object properties.

        Args:
            schema: Schema with nested properties
            indent: Indentation level

        Returns:
            Markdown-formatted documentation
        """
        lines = []
        properties = schema.get("properties", {})

        for key, prop_schema in properties.items():
            prop_type = prop_schema.get("type", "any")
            description = prop_schema.get("description", "No description")
            default = prop_schema.get("default")

            prefix = "  " * indent
            lines.append(f"{prefix}- **{key}** ({prop_type}): {description}")

            if default is not None:
                lines.append(f"{prefix}  - Default: `{default}`")

            if "minimum" in prop_schema:
                lines.append(f"{prefix}  - Minimum: {prop_schema['minimum']}")
            if "maximum" in prop_schema:
                lines.append(f"{prefix}  - Maximum: {prop_schema['maximum']}")

            if prop_type == "object" and "properties" in prop_schema:
                nested_docs = self._document_nested(prop_schema, indent + 1)
                lines.append(nested_docs)

        return "\n".join(lines)


# Global validator instance
_validator: ConfigValidator | None = None


def get_validator() -> ConfigValidator:
    """Get the global config validator instance.

    Returns:
        ConfigValidator instance
    """
    global _validator
    if _validator is None:
        _validator = ConfigValidator()
    return _validator


def validate_config(
    config: dict[str, Any], schema_name: str | None = None
) -> tuple[bool, list[str]]:
    """Validate configuration using global validator.

    Args:
        config: Configuration to validate
        schema_name: Optional specific schema name

    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = get_validator()
    return validator.validate(config, schema_name)


def apply_config_defaults(config: dict[str, Any], schema_name: str | None = None) -> dict[str, Any]:
    """Apply default values to configuration.

    Args:
        config: Configuration dictionary
        schema_name: Optional specific schema name

    Returns:
        Configuration with defaults applied
    """
    validator = get_validator()
    return validator.apply_defaults(config, schema_name)

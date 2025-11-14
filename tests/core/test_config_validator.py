"""Tests for configuration validator."""

from researcharr.core.config_validator import (
    ConfigValidator,
    apply_config_defaults,
    get_validator,
    validate_config,
)


class TestConfigValidator:
    """Test ConfigValidator class."""

    def test_init(self):
        """Test validator initialization."""
        validator = ConfigValidator()
        assert validator is not None
        assert len(validator._schemas) > 0

    def test_validate_valid_scheduling_config(self):
        """Test validation of valid scheduling configuration."""
        validator = ConfigValidator()
        config = {"scheduling": {"timezone": "America/New_York", "max_instances": 5}}

        is_valid, errors = validator.validate(config, "scheduling")

        assert is_valid
        assert len(errors) == 0

    def test_validate_invalid_type(self):
        """Test validation detects type errors."""
        validator = ConfigValidator()
        config = {"scheduling": {"timezone": 123}}  # Should be string

        is_valid, errors = validator.validate(config, "scheduling")

        assert not is_valid
        assert len(errors) > 0
        assert "type" in errors[0].lower()

    def test_validate_value_too_small(self):
        """Test validation detects values below minimum."""
        validator = ConfigValidator()
        config = {"scheduling": {"max_instances": 0}}  # Minimum is 1

        is_valid, errors = validator.validate(config, "scheduling")

        assert not is_valid
        assert len(errors) > 0
        assert "minimum" in errors[0].lower()

    def test_validate_value_too_large(self):
        """Test validation detects values above maximum."""
        validator = ConfigValidator()
        config = {"scheduling": {"max_instances": 100}}  # Maximum is 10

        is_valid, errors = validator.validate(config, "scheduling")

        assert not is_valid
        assert len(errors) > 0
        assert "maximum" in errors[0].lower()

    def test_validate_nested_config(self):
        """Test validation of nested configuration."""
        validator = ConfigValidator()
        config = {"database": {"monitoring": {"enabled": True, "health_check_interval": 300}}}

        is_valid, errors = validator.validate(config, "database")

        assert is_valid
        assert len(errors) == 0

    def test_validate_nested_invalid(self):
        """Test validation detects errors in nested config."""
        validator = ConfigValidator()
        config = {
            "database": {"monitoring": {"health_check_interval": 30}}  # Too small (minimum 60)
        }

        is_valid, errors = validator.validate(config, "database")

        assert not is_valid
        assert len(errors) > 0

    def test_validate_all_sections(self):
        """Test validating all sections in config."""
        validator = ConfigValidator()
        config = {
            "scheduling": {"timezone": "UTC"},
            "backups": {"retain_count": 5},
            "database": {"monitoring": {"enabled": True}},
        }

        is_valid, errors = validator.validate(config)

        assert is_valid
        assert len(errors) == 0

    def test_validate_unknown_schema(self):
        """Test validation with unknown schema name."""
        validator = ConfigValidator()
        config = {"unknown": {"key": "value"}}

        is_valid, errors = validator.validate(config, "unknown_schema")

        assert not is_valid
        assert "unknown schema" in errors[0].lower()

    def test_validate_missing_section(self):
        """Test validation with missing section uses defaults."""
        validator = ConfigValidator()
        config = {}  # Empty config

        is_valid, errors = validator.validate(config, "scheduling")

        assert is_valid  # Missing section is OK, uses defaults

    def test_apply_defaults_all(self):
        """Test applying defaults to all sections."""
        validator = ConfigValidator()
        config = {}

        result = validator.apply_defaults(config)

        assert "scheduling" in result
        assert result["scheduling"]["timezone"] == "UTC"
        assert "backups" in result
        assert result["backups"]["retain_count"] == 5

    def test_apply_defaults_specific_section(self):
        """Test applying defaults to specific section."""
        validator = ConfigValidator()
        config = {"scheduling": {}}

        result = validator.apply_defaults(config, "scheduling")

        assert result["scheduling"]["timezone"] == "UTC"
        assert result["scheduling"]["max_instances"] == 3
        assert result["scheduling"]["coalesce"] is True

    def test_apply_defaults_preserves_values(self):
        """Test that applying defaults preserves existing values."""
        validator = ConfigValidator()
        config = {"scheduling": {"timezone": "America/New_York"}}

        result = validator.apply_defaults(config, "scheduling")

        assert result["scheduling"]["timezone"] == "America/New_York"  # Preserved
        assert result["scheduling"]["max_instances"] == 3  # Default added

    def test_apply_defaults_nested(self):
        """Test applying defaults to nested configuration."""
        validator = ConfigValidator()
        config = {"database": {"monitoring": {}}}

        result = validator.apply_defaults(config, "database")

        assert result["database"]["monitoring"]["enabled"] is True
        assert result["database"]["monitoring"]["health_check_interval"] == 300

    def test_get_schema_docs_all(self):
        """Test getting documentation for all schemas."""
        validator = ConfigValidator()

        docs = validator.get_schema_docs()

        assert "scheduling" in docs.lower()
        assert "backups" in docs.lower()
        assert "database" in docs.lower()
        assert "timezone" in docs.lower()

    def test_get_schema_docs_specific(self):
        """Test getting documentation for specific schema."""
        validator = ConfigValidator()

        docs = validator.get_schema_docs("scheduling")

        assert "scheduling" in docs.lower()
        assert "timezone" in docs.lower()
        assert "max_instances" in docs.lower()
        assert "UTC" in docs  # Default value

    def test_get_schema_docs_unknown(self):
        """Test getting docs for unknown schema."""
        validator = ConfigValidator()

        docs = validator.get_schema_docs("unknown")

        assert "unknown" in docs.lower()


class TestConfigValidatorHelpers:
    """Test helper functions for config validation."""

    def test_get_validator_singleton(self):
        """Test that get_validator returns same instance."""
        validator1 = get_validator()
        validator2 = get_validator()

        assert validator1 is validator2

    def test_validate_config_helper(self):
        """Test validate_config helper function."""
        config = {"scheduling": {"timezone": "UTC"}}

        is_valid, errors = validate_config(config, "scheduling")

        assert is_valid
        assert len(errors) == 0

    def test_validate_config_invalid(self):
        """Test validate_config with invalid config."""
        config = {"scheduling": {"max_instances": 0}}

        is_valid, errors = validate_config(config, "scheduling")

        assert not is_valid
        assert len(errors) > 0

    def test_apply_config_defaults_helper(self):
        """Test apply_config_defaults helper function."""
        config = {"scheduling": {}}

        result = apply_config_defaults(config, "scheduling")

        assert result["scheduling"]["timezone"] == "UTC"


class TestConfigValidatorSchemas:
    """Test specific schema definitions."""

    def test_scheduling_schema_complete(self):
        """Test scheduling schema has all expected fields."""
        validator = ConfigValidator()
        schema = validator._schemas["scheduling"]

        props = schema["properties"]
        assert "timezone" in props
        assert "max_instances" in props
        assert "coalesce" in props

    def test_backups_schema_complete(self):
        """Test backups schema has all expected fields."""
        validator = ConfigValidator()
        schema = validator._schemas["backups"]

        props = schema["properties"]
        assert "enabled" in props
        assert "retain_count" in props
        assert "max_age_days" in props
        assert "check_interval" in props

    def test_database_schema_complete(self):
        """Test database schema has all expected fields."""
        validator = ConfigValidator()
        schema = validator._schemas["database"]

        props = schema["properties"]
        assert "monitoring" in props
        assert "path" in props

        # Check nested monitoring properties
        monitoring = props["monitoring"]["properties"]
        assert "enabled" in monitoring
        assert "health_check_interval" in monitoring
        assert "integrity_check_interval" in monitoring
        assert "size_alert_threshold_mb" in monitoring
        assert "fragmentation_threshold" in monitoring

    def test_storage_schema_complete(self):
        """Test storage schema has all expected fields."""
        validator = ConfigValidator()
        schema = validator._schemas["storage"]

        props = schema["properties"]
        assert "backup_path" in props
        assert "auto_vacuum" in props
        assert "wal_mode" in props


class TestConfigValidatorEdgeCases:
    """Test edge cases and error conditions."""

    def test_validate_empty_config(self):
        """Test validating empty configuration."""
        validator = ConfigValidator()
        config = {}

        is_valid, errors = validator.validate(config)

        assert is_valid  # Empty is OK

    def test_validate_unknown_properties(self):
        """Test that unknown properties are ignored."""
        validator = ConfigValidator()
        config = {"scheduling": {"timezone": "UTC", "unknown_prop": "value"}}

        is_valid, errors = validator.validate(config, "scheduling")

        assert is_valid  # Unknown properties ignored, not errors

    def test_validate_null_values(self):
        """Test validation with None values."""
        validator = ConfigValidator()
        config = {"scheduling": {"timezone": None}}

        is_valid, errors = validator.validate(config, "scheduling")

        # None may not match expected type
        assert not is_valid or "timezone" in str(errors)

    def test_apply_defaults_empty_section(self):
        """Test applying defaults to empty section."""
        validator = ConfigValidator()
        config = {"scheduling": {}}

        result = validator.apply_defaults(config, "scheduling")

        assert len(result["scheduling"]) > 0  # Has defaults

    def test_type_check_with_boolean_int(self):
        """Test that boolean False is not treated as 0."""
        validator = ConfigValidator()
        # In Python, bool is a subclass of int, so this might pass
        config = {"scheduling": {"coalesce": False}}

        is_valid, errors = validator.validate(config, "scheduling")

        assert is_valid  # False is a valid boolean

    def test_fragmentation_threshold_float(self):
        """Test that fragmentation threshold accepts floats."""
        validator = ConfigValidator()
        config = {"database": {"monitoring": {"fragmentation_threshold": 0.25}}}

        is_valid, errors = validator.validate(config, "database")

        assert is_valid

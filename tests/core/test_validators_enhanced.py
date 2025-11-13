"""Enhanced tests for researcharr/validators.py"""

from unittest.mock import Mock

import pytest

from researcharr import validators
from researcharr.repositories.exceptions import ValidationError
from researcharr.storage import models


class TestValidateManagedApp:
    """Test validate_managed_app edge cases"""

    def test_empty_name(self):
        """Should raise for empty name"""
        app = Mock(spec=models.ManagedApp)
        app.name = ""
        app.base_url = "http://localhost"
        app.api_key = "test"

        with pytest.raises(ValidationError, match="name must be a non-empty string"):
            validators.validate_managed_app(app)

    def test_whitespace_only_name(self):
        """Should raise for whitespace-only name"""
        app = Mock(spec=models.ManagedApp)
        app.name = "   "
        app.base_url = "http://localhost"
        app.api_key = "test"

        with pytest.raises(ValidationError, match="name must be a non-empty string"):
            validators.validate_managed_app(app)

    def test_none_name(self):
        """Should raise for None name"""
        app = Mock(spec=models.ManagedApp)
        app.name = None
        app.base_url = "http://localhost"
        app.api_key = "test"

        with pytest.raises(ValidationError, match="name must be a non-empty string"):
            validators.validate_managed_app(app)

    def test_empty_base_url(self):
        """Should raise for empty base_url"""
        app = Mock(spec=models.ManagedApp)
        app.name = "test"
        app.base_url = ""
        app.api_key = "test"

        with pytest.raises(ValidationError, match="base_url must be a valid URL"):
            validators.validate_managed_app(app)

    def test_invalid_base_url_no_scheme(self):
        """Should raise for base_url without scheme"""
        app = Mock(spec=models.ManagedApp)
        app.name = "test"
        app.base_url = "localhost"
        app.api_key = "test"

        with pytest.raises(ValidationError, match="base_url must be a valid URL"):
            validators.validate_managed_app(app)

    def test_none_base_url(self):
        """Should raise for None base_url"""
        app = Mock(spec=models.ManagedApp)
        app.name = "test"
        app.base_url = None
        app.api_key = "test"

        with pytest.raises(ValidationError, match="base_url must be a valid URL"):
            validators.validate_managed_app(app)

    def test_none_api_key(self):
        """Should raise for None api_key"""
        app = Mock(spec=models.ManagedApp)
        app.name = "test"
        app.base_url = "http://localhost"
        app.api_key = None

        with pytest.raises(ValidationError, match="api_key must be provided"):
            validators.validate_managed_app(app)

    def test_empty_string_api_key(self):
        """Should raise for empty string api_key"""
        app = Mock(spec=models.ManagedApp)
        app.name = "test"
        app.base_url = "http://localhost"
        app.api_key = ""

        with pytest.raises(ValidationError, match="api_key must be provided"):
            validators.validate_managed_app(app)

    def test_whitespace_only_api_key(self):
        """Should raise for whitespace-only api_key"""
        app = Mock(spec=models.ManagedApp)
        app.name = "test"
        app.base_url = "http://localhost"
        app.api_key = "   "

        with pytest.raises(ValidationError, match="api_key must be provided"):
            validators.validate_managed_app(app)

    def test_valid_http_url(self):
        """Should accept http:// URL"""
        app = Mock(spec=models.ManagedApp)
        app.name = "test"
        app.base_url = "http://localhost"
        app.api_key = "test"

        validators.validate_managed_app(app)  # Should not raise

    def test_valid_https_url(self):
        """Should accept https:// URL"""
        app = Mock(spec=models.ManagedApp)
        app.name = "test"
        app.base_url = "https://example.com"
        app.api_key = "test"

        validators.validate_managed_app(app)  # Should not raise

    def test_valid_custom_scheme_url(self):
        """Should accept custom scheme with ://"""
        app = Mock(spec=models.ManagedApp)
        app.name = "test"
        app.base_url = "custom://localhost"
        app.api_key = "test"

        validators.validate_managed_app(app)  # Should not raise


class TestValidateTrackedItem:
    """Test validate_tracked_item edge cases"""

    def test_empty_title(self):
        """Should raise for empty title"""
        item = Mock(spec=models.TrackedItem)
        item.title = ""
        item.arr_id = 1
        item.app_id = 1

        with pytest.raises(ValidationError, match="title must be a non-empty string"):
            validators.validate_tracked_item(item)

    def test_whitespace_only_title(self):
        """Should raise for whitespace-only title"""
        item = Mock(spec=models.TrackedItem)
        item.title = "   "
        item.arr_id = 1
        item.app_id = 1

        with pytest.raises(ValidationError, match="title must be a non-empty string"):
            validators.validate_tracked_item(item)

    def test_none_title(self):
        """Should raise for None title"""
        item = Mock(spec=models.TrackedItem)
        item.title = None
        item.arr_id = 1
        item.app_id = 1

        with pytest.raises(ValidationError, match="title must be a non-empty string"):
            validators.validate_tracked_item(item)

    def test_none_arr_id(self):
        """Should raise for None arr_id"""
        item = Mock(spec=models.TrackedItem)
        item.title = "test"
        item.arr_id = None
        item.app_id = 1

        with pytest.raises(ValidationError, match="arr_id must be a positive integer"):
            validators.validate_tracked_item(item)

    def test_zero_arr_id(self):
        """Should raise for zero arr_id"""
        item = Mock(spec=models.TrackedItem)
        item.title = "test"
        item.arr_id = 0
        item.app_id = 1

        with pytest.raises(ValidationError, match="arr_id must be a positive integer"):
            validators.validate_tracked_item(item)

    def test_negative_arr_id(self):
        """Should raise for negative arr_id"""
        item = Mock(spec=models.TrackedItem)
        item.title = "test"
        item.arr_id = -1
        item.app_id = 1

        with pytest.raises(ValidationError, match="arr_id must be a positive integer"):
            validators.validate_tracked_item(item)

    def test_none_app_id(self):
        """Should raise for None app_id"""
        item = Mock(spec=models.TrackedItem)
        item.title = "test"
        item.arr_id = 1
        item.app_id = None

        with pytest.raises(ValidationError, match="app_id must be set"):
            validators.validate_tracked_item(item)

    def test_valid_tracked_item(self):
        """Should accept valid tracked item"""
        item = Mock(spec=models.TrackedItem)
        item.title = "test"
        item.arr_id = 1
        item.app_id = 1

        validators.validate_tracked_item(item)  # Should not raise


class TestValidateSearchCycle:
    """Test validate_search_cycle edge cases"""

    def test_none_cycle_number(self):
        """Should raise for None cycle_number"""
        cycle = Mock(spec=models.SearchCycle)
        cycle.cycle_number = None

        with pytest.raises(ValidationError, match="cycle_number must be >= 1"):
            validators.validate_search_cycle(cycle)

    def test_zero_cycle_number(self):
        """Should raise for zero cycle_number"""
        cycle = Mock(spec=models.SearchCycle)
        cycle.cycle_number = 0
        cycle.total_items = 0

        with pytest.raises(ValidationError, match="cycle_number must be >= 1"):
            validators.validate_search_cycle(cycle)

    def test_negative_total_items(self):
        """Should raise for negative total_items"""
        cycle = Mock(spec=models.SearchCycle)
        cycle.cycle_number = 1
        cycle.total_items = -1
        cycle.items_searched = 0
        cycle.items_succeeded = 0
        cycle.items_failed = 0
        cycle.items_in_retry_queue = 0

        with pytest.raises(ValidationError, match="total_items must be >= 0"):
            validators.validate_search_cycle(cycle)

    def test_negative_items_searched(self):
        """Should raise for negative items_searched"""
        cycle = Mock(spec=models.SearchCycle)
        cycle.cycle_number = 1
        cycle.total_items = 0
        cycle.items_searched = -1
        cycle.items_succeeded = 0
        cycle.items_failed = 0
        cycle.items_in_retry_queue = 0

        with pytest.raises(ValidationError, match="items_searched must be >= 0"):
            validators.validate_search_cycle(cycle)

    def test_negative_items_succeeded(self):
        """Should raise for negative items_succeeded"""
        cycle = Mock(spec=models.SearchCycle)
        cycle.cycle_number = 1
        cycle.total_items = 0
        cycle.items_searched = 0
        cycle.items_succeeded = -1
        cycle.items_failed = 0
        cycle.items_in_retry_queue = 0

        with pytest.raises(ValidationError, match="items_succeeded must be >= 0"):
            validators.validate_search_cycle(cycle)

    def test_negative_items_failed(self):
        """Should raise for negative items_failed"""
        cycle = Mock(spec=models.SearchCycle)
        cycle.cycle_number = 1
        cycle.total_items = 0
        cycle.items_searched = 0
        cycle.items_succeeded = 0
        cycle.items_failed = -1
        cycle.items_in_retry_queue = 0

        with pytest.raises(ValidationError, match="items_failed must be >= 0"):
            validators.validate_search_cycle(cycle)

    def test_negative_items_in_retry_queue(self):
        """Should raise for negative items_in_retry_queue"""
        cycle = Mock(spec=models.SearchCycle)
        cycle.cycle_number = 1
        cycle.total_items = 0
        cycle.items_searched = 0
        cycle.items_succeeded = 0
        cycle.items_failed = 0
        cycle.items_in_retry_queue = -1

        with pytest.raises(ValidationError, match="items_in_retry_queue must be >= 0"):
            validators.validate_search_cycle(cycle)

    def test_completed_before_started(self):
        """Should raise when completed_at before started_at"""
        from datetime import datetime, timedelta

        cycle = Mock(spec=models.SearchCycle)
        cycle.cycle_number = 1
        cycle.total_items = 0
        cycle.items_searched = 0
        cycle.items_succeeded = 0
        cycle.items_failed = 0
        cycle.items_in_retry_queue = 0
        cycle.started_at = datetime.now()
        cycle.completed_at = cycle.started_at - timedelta(hours=1)

        with pytest.raises(ValidationError, match="completed_at cannot be before started_at"):
            validators.validate_search_cycle(cycle)

    def test_none_counter_skipped(self):
        """Should skip validation for None counter fields"""
        cycle = Mock(spec=models.SearchCycle)
        cycle.cycle_number = 1
        cycle.total_items = None
        cycle.items_searched = None
        cycle.items_succeeded = None
        cycle.items_failed = None
        cycle.items_in_retry_queue = None
        cycle.started_at = None
        cycle.completed_at = None

        validators.validate_search_cycle(cycle)  # Should not raise

    def test_valid_search_cycle(self):
        """Should accept valid search cycle"""
        from datetime import datetime

        cycle = Mock(spec=models.SearchCycle)
        cycle.cycle_number = 1
        cycle.total_items = 10
        cycle.items_searched = 10
        cycle.items_succeeded = 8
        cycle.items_failed = 2
        cycle.items_in_retry_queue = 0
        cycle.started_at = datetime.now()
        cycle.completed_at = None

        validators.validate_search_cycle(cycle)  # Should not raise


class TestValidateProcessingLog:
    """Test validate_processing_log edge cases"""

    def test_empty_event_type(self):
        """Should raise for empty event_type"""
        log = Mock(spec=models.ProcessingLog)
        log.event_type = ""
        log.message = "test"
        log.app_id = 1

        with pytest.raises(ValidationError, match="event_type must be provided"):
            validators.validate_processing_log(log)

    def test_whitespace_only_event_type(self):
        """Should raise for whitespace-only event_type"""
        log = Mock(spec=models.ProcessingLog)
        log.event_type = "   "
        log.message = "test"
        log.app_id = 1

        with pytest.raises(ValidationError, match="event_type must be provided"):
            validators.validate_processing_log(log)

    def test_none_event_type(self):
        """Should raise for None event_type"""
        log = Mock(spec=models.ProcessingLog)
        log.event_type = None
        log.message = "test"
        log.app_id = 1

        with pytest.raises(ValidationError, match="event_type must be provided"):
            validators.validate_processing_log(log)

    def test_event_type_too_long(self):
        """Should raise for event_type > 50 chars"""
        log = Mock(spec=models.ProcessingLog)
        log.event_type = "x" * 51
        log.message = "test"
        log.app_id = 1

        with pytest.raises(ValidationError, match="event_type must be <= 50 characters"):
            validators.validate_processing_log(log)

    def test_empty_message(self):
        """Should raise for empty message"""
        log = Mock(spec=models.ProcessingLog)
        log.event_type = "test"
        log.message = ""
        log.app_id = 1

        with pytest.raises(ValidationError, match="message must be provided"):
            validators.validate_processing_log(log)

    def test_whitespace_only_message(self):
        """Should raise for whitespace-only message"""
        log = Mock(spec=models.ProcessingLog)
        log.event_type = "test"
        log.message = "   "
        log.app_id = 1

        with pytest.raises(ValidationError, match="message must be provided"):
            validators.validate_processing_log(log)

    def test_none_message(self):
        """Should raise for None message"""
        log = Mock(spec=models.ProcessingLog)
        log.event_type = "test"
        log.message = None
        log.app_id = 1

        with pytest.raises(ValidationError, match="message must be provided"):
            validators.validate_processing_log(log)

    def test_none_app_id(self):
        """Should raise for None app_id"""
        log = Mock(spec=models.ProcessingLog)
        log.event_type = "test"
        log.message = "test message"
        log.app_id = None

        with pytest.raises(ValidationError, match="app_id must be set"):
            validators.validate_processing_log(log)

    def test_valid_processing_log(self):
        """Should accept valid processing log"""
        log = Mock(spec=models.ProcessingLog)
        log.event_type = "test"
        log.message = "test message"
        log.app_id = 1

        validators.validate_processing_log(log)  # Should not raise

    def test_event_type_exactly_50_chars(self):
        """Should accept event_type exactly 50 chars"""
        log = Mock(spec=models.ProcessingLog)
        log.event_type = "x" * 50
        log.message = "test"
        log.app_id = 1

        validators.validate_processing_log(log)  # Should not raise

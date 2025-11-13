"""README for Integration Tests

## Purpose

Integration tests verify that multiple components of researcharr work together correctly.
Unlike unit tests that test components in isolation, integration tests exercise:

- Real database operations (SQLite)
- API endpoints with Flask test client
- Plugin system with real plugin loading
- Multi-module logging flows
- Configuration file parsing

## Running Integration Tests

Run all integration tests:
```bash
pytest tests/integration/ -v
```

Run only integration tests (skip unit tests):
```bash
pytest tests/ -m integration
```

Run unit tests only (skip integration):
```bash
pytest tests/ -m "not integration"
```

## Test Organization

- `test_api_integration.py` - Full API workflow tests
- `test_database_integration.py` - Database + repository layer tests
- `test_plugin_integration.py` - Plugin loading and execution tests
- `test_logging_integration.py` - Cross-module logging tests

## Best Practices

1. **Use fixtures for setup/teardown**: Clean up resources properly
2. **Mark with @pytest.mark.integration**: Makes tests discoverable
3. **Keep tests focused**: Test one integration point per test
4. **Use descriptive names**: `test_api_creates_backup_and_lists_it`
5. **Clean up side effects**: Remove temp files, reset state

## Example

```python
import pytest

@pytest.mark.integration
def test_backup_api_creates_file_and_database_entry(client, db_session, tmp_path):
    \"\"\"Test that backup API creates both file and database record.\"\"\"
    # Create backup via API
    response = client.post('/api/backups/create')
    assert response.status_code == 200

    # Verify file exists
    backup_name = response.json['backup_name']
    backup_path = tmp_path / backup_name
    assert backup_path.exists()

    # Verify database record
    from researcharr.storage.repositories import BackupRepository
    repo = BackupRepository(db_session)
    backup = repo.get_by_name(backup_name)
    assert backup is not None
```

"""Integration tests for researcharr.

Integration tests verify interactions between multiple components of the
system, including:

- Database interactions with actual SQLite files
- API endpoints with Flask test client
- Plugin system with actual plugin instances
- Logging across multiple modules
- Configuration loading and parsing

These tests are marked with @pytest.mark.integration and can be run
separately from unit tests:

    pytest tests/integration/ -m integration

Integration tests may:
- Use temporary files and directories
- Make actual network calls (mocked for CI)
- Spawn subprocesses
- Take longer to execute than unit tests

For faster feedback during development, run unit tests first:

    pytest tests/ -m "not integration and not slow"
"""

# Testing Guide for researcharr

## Multi-Version Testing

Test across Python 3.10, 3.11, 3.12, 3.13, and 3.14 using Docker:

```bash
# Build and test all versions (first time or after dependency changes)
./scripts/ci-multi-version.sh

# Test using existing images (fast)
./scripts/ci-multi-version.sh --skip-build

# Test specific versions only
./scripts/ci-multi-version.sh --skip-build --versions "3.11 3.14"
```

The script builds debug Docker images for each Python version and runs smoke tests. Build logs and test outputs are saved to `/tmp/researcharr-*.log` for troubleshooting.

## Quick Start

Run all tests:
```bash
pytest tests/
```

This automatically uses pytest-xdist for parallel execution, but some tests marked with `@pytest.mark.no_xdist` will be skipped in workers and need a separate run.

## Complete Test Run

To run ALL tests including those that don't work well with xdist:

```bash
# Run parallel tests
pytest tests/ -v

# Run non-parallel tests
pytest tests/ -v -m no_xdist -n0
```

Or use the combined command:
```bash
pytest tests/ -v && pytest tests/ -v -m no_xdist -n0
```

## Test Markers

### `@pytest.mark.integration`
Integration tests that test multiple components together.
```bash
# Run only integration tests
pytest tests/ -m integration

# Skip integration tests
pytest tests/ -m "not integration"
```

### `@pytest.mark.slow`
Tests that take longer to execute.
```bash
# Skip slow tests for faster feedback
pytest tests/ -m "not slow"
```

### `@pytest.mark.logging`
Tests that manipulate logging state.
```bash
# Run only logging tests
pytest tests/ -m logging
```

### `@pytest.mark.no_xdist`
Tests that must run without pytest-xdist parallelization (typically because they use caplog in a way that doesn't work well with worker processes).
```bash
# Run these tests separately
pytest tests/ -m no_xdist -n0
```

## Why no_xdist?

Some tests use pytest's `caplog` fixture to capture log output. When running with pytest-xdist's process-level parallelization, logger configuration in worker processes can interfere with caplog's ability to capture logs.

Tests marked with `@pytest.mark.no_xdist` will:
1. Be skipped when xdist workers are active
2. Run successfully in the main pytest process (without `-n` flag)

This is a known limitation of pytest-xdist + caplog interaction.

## Test Organization

```
tests/
├── integration/       # Integration tests (multi-component)
├── unit/             # Unit tests (single component)
├── test_utils/       # Test utilities and helpers
│   └── logging_helpers.py  # Logging isolation helpers
├── run/              # run.py module tests (many use @no_xdist)
├── core/             # Core services tests
├── storage/          # Database and repository tests
└── ...
```

## Writing Tests with Logging

### ✅ Good: Use logging helpers

```python
from tests.test_utils.logging_helpers import isolated_logger

def test_something(tmp_path):
    with isolated_logger("my_logger", log_file=tmp_path / "test.log") as logger:
        logger.info("Test message")
        # Logger automatically cleaned up
```

### ✅ Good: Use the logging abstraction

```python
from researcharr.core.logging import get_logger

def test_something():
    logger = get_logger("test_logger")
    logger.info("Test message")
```

### ❌ Bad: Direct logging manipulation

```python
import logging

def test_something():
    logger = logging.getLogger()
    logger.handlers.clear()  # Breaks pytest's caplog!
```

See `CONTRIBUTING.md` and `.logging-lint-rules.md` for more details.

## Coverage

Run tests with coverage:
```bash
pytest tests/ --cov=researcharr --cov-report=html --cov-report=term-missing
```

View HTML coverage report:
```bash
open htmlcov/index.html
```

## CI/CD

The CI pipeline runs:
1. Parallel tests: `pytest tests/ -v`
2. Non-parallel tests: `pytest tests/ -v -m no_xdist -n0`
3. Coverage collection: `pytest tests/ --cov=researcharr --cov-report=xml`

Both must pass for the build to succeed.

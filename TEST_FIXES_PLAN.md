# Flaky Test Fixes Plan

## Problem Summary
- **9 tests failing in CI** (99.4% pass rate - 1475/1484 passing)
- **All tests pass locally** (100% pass rate)
- Primary issue: Tests are sensitive to execution order and global state

## Identified Failing Tests

Based on CI logs analysis, the failures are primarily in factory tests:

1. `tests/factory/test_factory_batch7.py::test_setup_generates_api_and_persists`
   - Error: `AssertionError: assert False is True`
   - Issue: Module state not properly reset between tests

2. `tests/factory/test_factory_batch5.py::test_updates_upgrade_in_image_and_invalid_url`
   - Error: `AttributeError: <module 'researcharr.factory'> has no attribute '_running_i...'`
   - Issue: Global module attributes not cleaned up

## Root Causes

### 1. Non-Deterministic Test Execution
- pytest-xdist runs tests in parallel across workers
- Test execution order varies between runs
- No fixed random seed for pytest-randomly

### 2. Global State Pollution
- **Logging singletons**: Multiple tests configure root logger
- **Prometheus registries**: Metrics collectors persist between tests
- **Module-level state**: Factory module state not isolated
- **Import caching**: sys.modules cache affects fresh imports

### 3. CI vs Local Environment Differences
- CI uses PYTHONPATH with site-packages (installed package mode)
- Local uses project root in path (editable/development mode)
- Different import resolution affects module identity checks

## Solution Strategy

### Phase 1: Add Deterministic Configuration
```python
# pyproject.toml additions
[tool.pytest.ini_options]
addopts = [
    "--randomly-seed=42",           # Fixed seed for reproducibility
    "--randomly-dont-reorganise",   # Keep class methods together
    "-n", "auto",                   # xdist with auto worker count
    "--dist=loadgroup",             # Group tests by file for isolation
]
```

### Phase 2: Add State Isolation Fixtures

Create `tests/conftest_fixes.py`:

```python
import logging
import sys
from prometheus_client import REGISTRY
import pytest

@pytest.fixture(autouse=True, scope="function")
def isolate_logging():
    """Reset logging configuration between tests."""
    # Save original state
    original_level = logging.root.level
    original_handlers = logging.root.handlers[:]

    yield

    # Restore original state
    logging.root.setLevel(original_level)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    for handler in original_handlers:
        logging.root.addHandler(handler)

@pytest.fixture(autouse=True, scope="function")
def isolate_prometheus():
    """Clean up Prometheus collectors between tests."""
    # Get list of collectors before test
    before = set(REGISTRY._collector_to_names.keys())

    yield

    # Remove collectors added during test
    after = set(REGISTRY._collector_to_names.keys())
    for collector in after - before:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass

@pytest.fixture(autouse=True, scope="function")
def isolate_factory_state():
    """Reset factory module state between tests."""
    factory_modules = [
        'researcharr.factory',
        'factory',
    ]

    # Save module state
    saved_modules = {}
    for mod_name in factory_modules:
        if mod_name in sys.modules:
            saved_modules[mod_name] = sys.modules[mod_name]

    yield

    # Restore or clean up modules
    for mod_name in factory_modules:
        if mod_name in saved_modules:
            sys.modules[mod_name] = saved_modules[mod_name]
        elif mod_name in sys.modules:
            del sys.modules[mod_name]
```

### Phase 3: Fix Specific Test Issues

#### Fix 1: test_setup_generates_api_and_persists
```python
# Add explicit cleanup in test
def test_setup_generates_api_and_persists():
    # ... existing test code ...

    # Explicit cleanup
    if hasattr(researcharr.factory, '_api_generated'):
        delattr(researcharr.factory, '_api_generated')
```

#### Fix 2: test_updates_upgrade_in_image_and_invalid_url
```python
# Add defensive attribute checks
def test_updates_upgrade_in_image_and_invalid_url():
    # Reset state if it exists
    for attr in ['_running_in_image', '_upgrade_available']:
        if hasattr(researcharr.factory, attr):
            delattr(researcharr.factory, attr)

    # ... existing test code ...
```

### Phase 4: Update pytest Configuration

```toml
# pyproject.toml - Enhanced configuration
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

addopts = [
    "-v",
    "--strict-markers",
    "--strict-config",
    "--log-file=${TMPDIR:-/tmp/ci}/pytest.log",
    "--log-file-level=DEBUG",
    "--log-cli-level=INFO",
    "--tb=short",
    "--randomly-seed=42",
    "--randomly-dont-reorganise",
    "-n", "auto",
    "--dist=loadgroup",
    "--maxfail=3",
]

markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]

# Ensure xdist doesn't cause race conditions
xdist_group_by_class = true
```

## Implementation Order

1. ✅ Created test/fix-flaky-ci-tests branch
2. Add deterministic pytest config
3. Add autouse fixtures for state isolation
4. Fix specific test issues
5. Run local tests to verify (should still pass 100%)
6. Push to CI and verify (target: 100% pass rate)
7. Document findings and add to CI best practices

## Success Criteria

- [ ] All 1484 tests pass in CI (100% pass rate)
- [ ] Tests remain deterministic across multiple CI runs
- [ ] Local tests continue to pass (100% pass rate)
- [ ] No new flaky test warnings
- [ ] Documentation updated with lessons learned

## Related Files

- `pyproject.toml` - pytest configuration
- `tests/conftest.py` - existing fixtures
- `tests/conftest_fixes.py` - new isolation fixtures (to create)
- `tests/factory/test_factory_batch5.py` - failing test
- `tests/factory/test_factory_batch7.py` - failing test
- `.github/workflows/ci-wheels-and-test.yml` - CI configuration

## References

- [pytest-randomly documentation](https://github.com/pytest-dev/pytest-randomly)
- [pytest-xdist best practices](https://pytest-xdist.readthedocs.io/)
- [Isolated test patterns](https://docs.pytest.org/en/stable/how-to/fixtures.html#autouse-fixtures)

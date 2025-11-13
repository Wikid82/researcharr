Contributing to researcharr

Thank you for your interest in contributing. The canonical contributor guidelines are included in this repository under `docs/`. Please read `docs/Contributing.md` for full guidance.

Quick start (developer checklist)

1. Create and activate a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run formatting and import sorting (these are required to match CI):

```bash
isort --profile=black .
black .
```

3. Run pre-commit and tests:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
python -m pytest tests/ -v
```

Recommended developer command (same as used in CI-friendly helpers):

```bash
isort --profile=black . && black . && python -m pytest tests/
```

Logging Best Practices

To prevent test pollution and ensure proper logging behavior:

**Use the logging abstraction layer:**
```python
from researcharr.core.logging import get_logger
logger = get_logger(__name__)
logger.info("Application started")
```

**In tests, use the logging helpers:**
```python
from tests.test_utils.logging_helpers import isolated_logger

def test_something(tmp_path):
    with isolated_logger("my_logger", log_file=tmp_path / "test.log") as logger:
        logger.info("Test message")
        # Logger automatically cleaned up after block
```

**Never do these in application or test code:**
- ❌ `logging.getLogger().handlers.clear()` - Breaks pytest's caplog
- ❌ `logging.basicConfig()` - Affects global state
- ❌ Direct manipulation of `logger.handlers` without restoration
- ❌ Adding handlers without checking for duplicates

See `.logging-lint-rules.md` for detailed patterns to avoid.

Branching and PRs

- Target the `development` branch for feature and bugfix PRs. `main` is the release branch.

If you have questions, open an issue or ask on the PR. Thank you for contributing!

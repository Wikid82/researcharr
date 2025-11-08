# Coverage Differences: CI vs Local

## Problem

CI reports **59% coverage** while local development shows **64% coverage** - a 5% discrepancy.

## Root Cause

The difference is caused by how Python resolves imports:

- **CI Environment**: Prepends site-packages to `PYTHONPATH`, making pytest prefer the **installed package**
- **Local Environment**: Uses default import resolution, preferring **local source files** in the repo

This affects which files are measured and how coverage is calculated, particularly for:
- `researcharr/__init__.py` (1280 lines, 37% coverage)
- `researcharr/_factory_proxy.py` (440 lines, 51% coverage)
- `researcharr/core/services.py` (533 lines, 56% coverage)
- `researcharr/webui.py` (55 lines, 0% coverage in CI)

## CI Configuration

From `.github/workflows/ci.yml`:

```bash
# Detect site-packages for the chosen interpreter
SITE_PACKAGES=$(python -c 'import sysconfig, json; print(sysconfig.get_paths()["purelib"])')
export PYTHONPATH="$SITE_PACKAGES:$PYTHONPATH"

# Run tests
pytest tests/ \
  --maxfail=3 --disable-warnings -v \
  --cov=researcharr --cov-report=xml:coverage.xml
```

## Solutions

### Option 1: Match Local to CI (Recommended)

Run tests locally using the same environment as CI:

```bash
# Using the script
./scripts/test-ci-mode.sh

# Or manually
SITE_PACKAGES=$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
export PYTHONPATH="$SITE_PACKAGES:$PYTHONPATH"
pytest tests/ --cov=researcharr --cov-report=term-missing --cov-report=html --cov-report=xml
```

**VS Code Tasks**: The default "Run Tests with Coverage" task now uses CI mode.

### Option 2: Match CI to Local

Remove the `PYTHONPATH` manipulation from CI:

```yaml
# In .github/workflows/ci.yml, remove these lines:
SITE_PACKAGES=$(python -c 'import sysconfig, json; print(sysconfig.get_paths()["purelib"])')
export PYTHONPATH="$SITE_PACKAGES:$PYTHONPATH"
```

⚠️ **Not recommended**: The CI setup was intentionally configured this way to ensure tests use the installed package, not repo files.

### Option 3: Improve Coverage

The best long-term solution is to improve test coverage of the low-coverage files:

1. **researcharr/__init__.py** (37% coverage)
   - Large shim file with module reconciliation logic
   - Many conditional branches not exercised in tests
   - Consider splitting into smaller, testable modules

2. **_factory_proxy.py** (51% coverage)
   - Factory proxy patterns need more test scenarios

3. **core/services.py** (56% coverage)
   - Service initialization paths need coverage

4. **webui.py** (0% coverage in CI, 94% locally)
   - Import path differences causing measurement issues

## Current State

- **Coverage Threshold**: Set to 59% (matching CI reality)
- **Local Coverage**: ~64% (using local source)
- **CI Coverage**: ~59% (using installed package)
- **Target**: Raise to 85% after improving coverage

## Investigation Needed

Why does the import path affect coverage so significantly?

Possible reasons:
1. Different Python versions tested in CI (3.10-3.14) vs local (3.13)
2. Module reconciliation logic in `researcharr/__init__.py` behaves differently
3. Some modules not being imported in CI but are in local tests
4. Coverage measurement differences between installed vs editable installs

## References

- Issue: [#107 - Processing Pipeline Framework](https://github.com/Wikid82/researcharr/issues/107)
- PR: [#135 - WIP: Processing Pipeline Framework](https://github.com/Wikid82/researcharr/pull/135)
- Commit: cf88550f721b10fb3cb8a2cca06ce1633ce4cd95 (lowered threshold to 59%)
- Related Files:
  - `.github/workflows/ci.yml` (CI configuration)
  - `pyproject.toml` (coverage settings)
  - `.vscode/tasks.json` (VS Code test tasks)
  - `scripts/test-ci-mode.sh` (CI-matching test script)

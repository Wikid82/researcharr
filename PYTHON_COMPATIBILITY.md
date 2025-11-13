# Python Version Compatibility

## Supported Versions

Researcharr supports Python **3.10+** to ensure compatibility with the broadest range of deployment environments, including:
- Docker containers
- System packages (deb, rpm, etc.)
- pip/PyPI installations
- Source installations

## Compatibility Layer

The `researcharr/compat.py` module provides compatibility shims for features introduced in newer Python versions:

### datetime.UTC (Python 3.11+)

**Issue**: Python 3.11 introduced `datetime.UTC` as a constant. Python 3.10 only has `datetime.timezone.utc`.

**Solution**: The compat module provides `UTC` that works across all supported versions:

```python
# Don't do this (breaks Python 3.10):
from datetime import UTC, datetime

# Do this instead:
from datetime import datetime
from researcharr.compat import UTC
```

### werkzeug.__version__

**Issue**: Modern Werkzeug versions removed the `__version__` attribute.

**Solution**: The compat module automatically adds `werkzeug.__version__` using `importlib.metadata` if it's missing.

## Testing Across Python Versions

### Docker-Based Testing

Test with different Python versions using the parameterized Dockerfile:

```bash
# Build Python 3.10 debug image
docker build --target debug --build-arg PY_VERSION=3.10 -t researcharr:py310-debug .

# Run tests in Python 3.10
docker run --rm -t --entrypoint pytest -w /app researcharr:py310-debug -q

# Test with Python 3.11
docker build --target debug --build-arg PY_VERSION=3.11 -t researcharr:py311-debug .
docker run --rm -t --entrypoint pytest -w /app researcharr:py311-debug -q

# Test with Python 3.12
docker build --target debug --build-arg PY_VERSION=3.12 -t researcharr:py312-debug .
docker run --rm -t --entrypoint pytest -w /app researcharr:py312-debug -q
```

### Local Testing with tox

Use tox to test multiple Python versions locally:

```bash
# Test all configured Python versions
tox

# Test specific Python version
tox -e py310
tox -e py311
tox -e py312
```

## Guidelines for Contributors

When adding new code:

1. **Avoid Python 3.11+ only features** without compatibility fallbacks:
   - `datetime.UTC` → use `researcharr.compat.UTC`
   - Pattern matching (`match`/`case`) → use if/elif or dict dispatch
   - `tomllib` → use `tomli` package for 3.10 compatibility
   - Type parameter syntax (`type X = ...`) → use traditional typing

2. **Test with Python 3.10** before submitting PRs

3. **Use the compat module** for version-specific features

4. **Check compatibility** if importing from:
   - `datetime` (UTC, ISO format parsing)
   - `typing` (new syntax in 3.10+)
   - `functools` (new decorators/utilities)
   - Standard library modules with 3.11+ additions

## Package Distribution

Researcharr aims to match *arr suite distribution formats:

- **Docker images** (multi-architecture)
- **Debian packages** (`.deb`)
- **RPM packages** (`.rpm`)
- **PyPI/pip** (wheels + source)
- **Portable binaries** (PyInstaller/Nuitka)

These packages may be deployed on systems with varying Python versions, so **broad compatibility is essential** for user convenience.

## Version Support Policy

- **Minimum supported**: Python 3.10 (released Oct 2021)
- **Recommended**: Python 3.11+ for best performance
- **Tested**: All minor versions from 3.10 through latest stable
- **Future**: When Python 3.10 reaches EOL (Oct 2026), minimum will move to 3.11

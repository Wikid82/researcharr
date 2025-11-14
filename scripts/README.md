# Scripts Directory

Automation and utility scripts for researcharr development and CI.

## CI Scripts

### `ci-local.sh`
Single-version local CI runner that mirrors GitHub Actions workflow.

**Usage:**
```bash
# Full run: install deps, pre-commit, pytest, Docker build, Trivy scan
./scripts/ci-local.sh

# Skip dependency installation
./scripts/ci-local.sh --skip-install

# Skip Docker build and Trivy scan
./scripts/ci-local.sh --no-docker --no-trivy
```

**What it does:**
- Installs Python dependencies
- Runs pre-commit hooks
- Executes pytest with coverage
- Builds Docker image and runs Trivy security scan (optional)

### `ci-multi-version.sh`
Multi-version testing across Python 3.10-3.14 using Docker.

**Usage:**
```bash
# Build and test all versions (first time or after dependency changes)
./scripts/ci-multi-version.sh

# Test using existing images (fast)
./scripts/ci-multi-version.sh --skip-build

# Test specific versions only
./scripts/ci-multi-version.sh --versions "3.11 3.12 3.14"

# Show help
./scripts/ci-multi-version.sh --help
```

**What it does:**
- Builds debug Docker images for specified Python versions
- Runs smoke tests (tests/run/test_run.py) in each image
- Provides colored summary of build and test results
- Saves logs to `/tmp/researcharr-{build|test}-{version}.log`

**Images created:**
- `researcharr:py310-debug`
- `researcharr:py311-debug`
- `researcharr:py312-debug`
- `researcharr:py313-debug`
- `researcharr:py314-debug`

Debug images include full development dependencies (requirements-dev.txt) for interactive debugging.

## Other Scripts

### `debug-collect.sh`
Collects system and application debug information for troubleshooting.

## Development Workflow

**Pre-commit check:**
```bash
./scripts/ci-local.sh --no-docker --no-trivy
```

**Test version compatibility:**
```bash
# After changing dependencies
./scripts/ci-multi-version.sh

# Quick check with existing images
./scripts/ci-multi-version.sh --skip-build
```

**Full CI validation:**
```bash
./scripts/ci-local.sh
```

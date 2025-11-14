# Copilot Coding Agent Instructions for `researcharr`

These instructions guide the GitHub Copilot coding agent when making changes in this repository.

## Repository Overview

- **Project name:** `researcharr`
- **Purpose:** Utility to automatically trigger searches in the *arr* suite to keep files in sync with scoring or custom format changes.
- **Primary language:** Python
- **Key characteristics:**
  - Python application with automated tests.
  - CI and multi-version testing are driven by scripts in `scripts/`.
  - Integration tests live under `tests/integration/`.

_Copilot: Before making changes, inspect `README.md`, `scripts/README.md`, and the `tests/` layout to align with the current architecture and workflow._

## Code Layout and Important Paths

- **Application code:**  
  - Look under top-level Python package directories (e.g., `researcharr/`) for core logic.
- **Tests:**
  - Unit tests: under `tests/` (excluding `tests/integration/`).
  - Integration tests: under `tests/integration/` (see `tests/integration/README.md`).
- **Scripts and tooling:**
  - `scripts/`: automation and CI helpers (see `scripts/README.md`).
    - `ci-local.sh` – local CI workflow (deps, pre-commit, pytest, Docker, Trivy).
    - `ci-multi-version.sh` – multi-version testing across Python 3.10–3.14.
- **GitHub and release tooling (for awareness):**
  - `release-drafter-action/` and `.github/` workflows may orchestrate CI and releases.

_Copilot: When adding new modules or scripts, mirror the existing directory structure and naming patterns in the nearest related files._

## Coding Conventions

- **Language & style:**
  - Use idiomatic Python.
  - Follow the formatting and import style of nearby code (e.g., type hints, logging patterns, error handling).
- **Structure:**
  - Prefer small, focused functions.
  - Reuse existing helpers instead of duplicating logic when possible.
- **Naming:**
  - Use descriptive, snake_case names for functions and variables.
  - Use clear, descriptive test names (e.g., `test_api_creates_backup_and_lists_it`).

_Copilot: When modifying an area of code, first look at existing files in that directory to infer style, patterns, and abstractions, and then follow them closely._

## Testing Guidance

- **Test frameworks:** `pytest`
- **Running tests (developer workflow):**
  - For a quick local check without Docker/Trivy:
    ```bash
    ./scripts/ci-local.sh --no-docker --no-trivy
    ```
  - Full CI-like validation:
    ```bash
    ./scripts/ci-local.sh
    ```
  - Multi-version testing (Python 3.10–3.14):
    ```bash
    ./scripts/ci-multi-version.sh
    ```
  - Integration tests only:
    ```bash
    pytest tests/integration/ -v
    # or
    pytest tests/ -m integration
    ```
  - Unit tests only (skip integration):
    ```bash
    pytest tests/ -m "not integration"
    ```

- **Where to put tests:**
  - For new or modified functionality, add/adjust tests in the corresponding file under `tests/`.
  - For cross-component behavior or interactions (API + DB + plugins + logging), add or update tests in `tests/integration/`, following `tests/integration/README.md`.

_Copilot: For any non-trivial change, add or update tests. If similar tests exist, follow their structure and style; if not, create new tests mirroring the closest existing patterns._

## Integration Tests Expectations

From `tests/integration/README.md`:

- Integration tests cover:
  - Real SQLite DB operations
  - API endpoints via Flask test client
  - Plugin loading and execution
  - Multi-module logging flows
  - Configuration parsing

- Best practices:
  - Use fixtures for setup/teardown.
  - Mark integration tests with `@pytest.mark.integration`.
  - Keep tests focused and use descriptive names.
  - Clean up side effects (temp files, DB state, etc.).

_Copilot: When extending integration coverage, follow the patterns in `tests/integration/*.py` and keep each test focused on a single integration flow._

## CI, Docker, and Local Development

- **Local CI scripts (preferred for validating changes):**
  - Use `./scripts/ci-local.sh` and `./scripts/ci-multi-version.sh` rather than manually orchestrating all steps whenever possible.
- **Logs and debugging:**
  - Multi-version testing logs are stored under `/tmp/researcharr-{build|test}-{version}.log`.

_Copilot: If you introduce new CI-relevant behavior (e.g., environment variables, script interfaces), update both the relevant scripts under `scripts/` and, if needed, any CI workflow definitions so they stay in sync._

## Documentation

- **Scripts documentation:** `scripts/README.md`
- **Integration tests documentation:** `tests/integration/README.md`
- Other documentation may be present in additional `README.md` files or under `docs/` if that directory exists.

_Copilot: When adding new developer-facing behavior (scripts, significant features, or new workflows), update the nearest relevant README to document usage and expectations._

## Security, Secrets, and Safety

- Do not hardcode secrets, tokens, or credentials.
- Prefer environment variables or existing configuration patterns for sensitive values.
- Avoid adding verbose logs that may contain sensitive data.

_Copilot: If you need to touch authentication, configuration, or external API integration, follow existing patterns and avoid introducing new ways of handling secrets unless explicitly requested._

## Pull Request Scope and Behavior

When preparing changes (for a PR):

1. Keep changes **narrowly scoped** to the described problem or enhancement.
2. Avoid large, sweeping refactors unless explicitly requested.
3. Maintain backwards compatibility unless the task clearly calls for a breaking change.
4. Ensure:
   - Tests pass locally (at least `./scripts/ci-local.sh --no-docker --no-trivy`).
   - New code is covered by tests where practical.
   - Relevant documentation is updated.

_Copilot: In commit and PR descriptions, include a brief summary of the problem, the high-level approach, and any notable trade-offs or limitations._

## When Unsure

_Copilot:_

- Prefer minimal, incremental changes that match existing patterns over introducing new frameworks or large abstractions.
- If there are multiple plausible implementations, choose the simplest one that:
  1. Matches current code style and architecture.
  2. Is easy to test with the existing pytest/CI setup.
  3. Minimizes configuration and deployment impact.

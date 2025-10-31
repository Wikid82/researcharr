Recent Changes

This page summarizes the recent repository changes that contributors should be aware of.

Highlights

- CI and formatting
  - CI now runs on every push and pull request and performs linting (`flake8`), formatting checks (`black`, `isort`), type checks (`mypy`), and tests (`pytest`).
  - `isort` is configured to use Black's import style via `researcharr/.isort.cfg`.
  - CI uses pip caching to speed up dependency installs.
  - Formatting is run in check-only mode in CI; contributors should run `isort --profile=black .` and `black .` locally before committing.

- Pre-commit
  - `.pre-commit-config.yaml` at the repository root includes hooks for Black, isort, flake8, and other checks. Running `pre-commit install` will ensure checks run locally before commits.

- Docker publishing
  - Docker images are built and pushed to GHCR per-branch. Branch-specific tags are used and special tags exist for `main` and `development`.
  - The Docker build workflow uses build-cache and pip cache to speed up CI.

Note: Branch images are published automatically after CI passes for a push. This enables QA teams and contributors to pull a branch-tagged image for testing (e.g., `ghcr.io/wikid82/researcharr:plugins`).

- Documentation & Roadmap
  - `researcharr/ROADMAP.md` and wiki `Roadmap.md` updated to include Packaging & Distribution notes and reprioritized feature goals (app-first focus, move away from cron jobs for scheduling over time, add WebSocket-based UI improvements, release-aware processing, and webhook/Apprise notifications).

- Formatting fixes
  - Several small code and test files were auto-formatted and had import ordering adjusted to satisfy the new `isort`/`black` configuration.

Why this matters

- These changes enforce consistent formatting and import ordering across the codebase, which reduces code review noise.
- The CI checks will catch style, import ordering, and test regressions early.
- The Docker publishing improvements make CI faster and publishing predictable.

If you notice any CI failures after merging these changes, run the local auto-fixers and push the resulting commit. If a test is failing, include the failing test output in your PR discussion for faster triage.

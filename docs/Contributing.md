# Contributing to researcharr

Thank you for your interest in contributing! This project welcomes new contributors. Please read the guidelines below to get started.

## Branching Workflow

- The `main` branch is always stable and production-ready.
- The `development` branch is for active development and integration.
- All new features and fixes should be developed in feature branches off of `development`.

**Typical workflow:**

1. Make sure you have the latest code:
  ```bash
  git checkout main
  git pull origin main
  git checkout development
  git pull origin development
  ```
2. Create a feature branch:
  ```bash
  git checkout -b feature/your-feature
  # ...work, commit, push...
  git push -u origin feature/your-feature
  ```
3. Open a pull request (PR) to merge your feature branch into `development` (the main integration branch). Small bugfixes or docs-only changes may be opened directly against `development`.
4. When `development` is stable and tested, it will be merged into `main` for releases.

## Getting Started
- Fork the repository and clone your fork.
- Create a new branch for your feature or bugfix.
- Install dependencies with `pip install -r requirements.txt` (or use Docker for a containerized dev environment). We recommend using a virtualenv as described below.

## Development Environment
- Python 3.8+ is required.
- Use a virtual environment (`python -m venv .venv && source .venv/bin/activate`).
- All dependencies are listed in `requirements.txt`.

## Running Tests
- All code changes should be covered by tests.
- Run the full test suite with:
  ```bash
  python -m pytest tests/ -v
  ```
- Tests cover config loading, error handling, database integrity, and web UI endpoints.

Before opening a PR, run the auto-fixers and pre-commit hooks (see Formatting & pre-commit checklist).

## CI and Docker notes

The project runs CI (lint, type checks, and tests) automatically on every push and every pull request via `.github/workflows/ci.yml`. CI uses pip caching to speed up installs. Please run tests and formatters locally before opening PRs.

Docker images are built for all branches and published to GitHub Container Registry, tagged by branch name (e.g. `ghcr.io/wikid82/researcharr:feature-xyz`). If you want to avoid images from forks or PRs, open an issue or ping a maintainer — we can restrict publishes to `push` events on the main repository only.

### Formatting & pre-commit checklist

Run the auto-fixers locally to match CI checks before committing:

```bash
isort --profile=black .
black .
```

Install and use pre-commit to catch issues early:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Suggested commit message style:

- Use imperative, present-tense style: "Add feature X", "Fix bug Y".
- Reference related issues when relevant: "Fixes #123".

## Submitting Changes
- Push your branch to your fork and open a pull request (PR) against the `development` branch.
- Describe your changes and reference any related issues.
- Ensure all tests pass and formatters are run before requesting review.

## Code Review
- PRs are reviewed for correctness, clarity, and test coverage.
- Address any requested changes promptly.
- Squash commits if requested.

## Project Roadmap & Goals
- See the [Roadmap](Roadmap.md) in this `docs/` folder for project direction and priorities.

## Questions or Help?
- Check the documentation in this `docs/` folder (for example `Getting-Started.md`) or open an issue on GitHub.
- For major changes, open a discussion or issue first to get feedback.

---

Happy coding!

Contributing to researcharr

Thank you for your interest in contributing. The canonical, detailed contributor guidelines live in the repository wiki. Please read the wiki `Contributing.md` for full guidance:

- researcharr wiki: https://github.com/Wikid82/researcharr/wiki/Contributing

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

Branching and PRs

- Target the `development` branch for feature and bugfix PRs. `main` is the release branch.

If you have questions, open an issue or ask on the PR. Thank you for contributing!

<div align="center">
  <img src="static/logo.webp" alt="researcharr logo" height="120" />

<p>
  <a href="https://codecov.io/github/Wikid82/researcharr"><img src="https://codecov.io/github/Wikid82/researcharr/graph/badge.svg?token=LBEJBSUPLX" alt="codecov"/></a>
  <a href="https://github.com/Wikid82/researcharr/actions/workflows/ci.yml"><img src="https://github.com/Wikid82/researcharr/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://github.com/Wikid82/researcharr/commits"><img src="https://img.shields.io/github/last-commit/Wikid82/researcharr" alt="last commit"/></a>
  <a href="LICENSE"><img alt="License: GPL v3" src="https://img.shields.io/badge/License-GPLv3-blue.svg"/></a>
  <br>
  <a href="https://github.com/Wikid82/researcharr/actions/workflows/pages-deploy.yml"><img src="https://github.com/Wikid82/researcharr/actions/workflows/pages-deploy.yml/badge.svg" alt="Docs"/></a>
  <br>
  <img src="https://ghchart.rshah.org/Wikid82" alt="Wikid82's GitHub contributions"/>
</p>
</div>

# researcharr — Day One

This repository contains the early-stage code for researcharr. We're in a
Day One phase: focusing on building and validating core library and
processing functionality. Higher-level features (web UI, packaged images,
and detailed operator guides) are planned in `ROADMAP.md` and will be added
after the core is proven.

Status
------
- Phase: Core development (library and processing code)
- CI: tests & linting focused; Docker builds are paused by default to keep
  feedback fast.

Quick start for developers
--------------------------
1. Create and activate a venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install runtime and development dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
```

3. Run formatting, linters and tests:

```bash
pre-commit run --all-files
pytest tests/ --maxfail=3 -q
```

What we're building (short outline)
-----------------------------------
- A compact engine to validate and trigger searches against Radarr/Sonarr-like
  services.
- Durable scheduling and queueing using SQLite for Day One.
- Observability primitives: `/health`, logs, and basic metrics endpoints.
- Optional web UI, packaged Docker images, and extended operator docs (deferred
  until core functionality is stable).

Contributing
------------
- Start by writing unit tests for core modules under `tests/`.
- Use the `ci-tests-only.yml` workflow (pre-commit + pytest) for fast CI
  feedback.
- See `docs/Contributing.md` for how to submit PRs and the contributor
  workflow.

License
-------
MIT — see `LICENSE`.

Notes
-----
- This README intentionally keeps scope and instructions minimal until core
  functionality is validated. See `ROADMAP.md` for planned features and
  acceptance criteria.

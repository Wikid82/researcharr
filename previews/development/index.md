# researcharr documentation

Welcome — this repository contains the documentation that powers the project website and GitHub Pages site. Use these pages for quick onboarding, deployment guidance, CI notes, and operational reference.

Below is a suggested table of contents (order follows the README and operator/developer flow):

## Table of contents

1. [Getting Started](Getting-Started.md) — Quick start for running researcharr locally or in Docker, initial credentials, and basic configuration.
2. [Environment variables](Environment-Variables.md) — All runtime environment variables (PUID, PGID, TIMEZONE, WEBUI_PORT, and more) with examples.
3. [Deployment and Resource Recommendations](Deployment-and-Resources.md) — Docker / Compose / Kubernetes examples and job/runtime caps (JOB_TIMEOUT, JOB_RLIMIT_AS_MB, JOB_RLIMIT_CPU_SECONDS).
4. [Health and Metrics](Health-and-Metrics.md) — `/health` and `/metrics` endpoints, Docker healthcheck examples, and metrics exposed by the app.
5. [Versioning & Releases](Versioning.md) — Image labels, `/api/version`, CI tagging and best practices for tracing builds.
6. [Packaging and Distribution](Packaging-and-Distribution.md) — Packaging targets, CI packaging jobs, and recommended approaches for releases.
7. [CI and Development](CI-and-Development.md) — CI checks, formatting, pre-commit guidance, and branch/PR workflow for contributors.
8. [Contributing](Contributing.md) — Contributor guide, branching model, tests, and pre-commit checklist.
9. [PR Instructions](PR_INSTRUCTIONS.txt) — Quick commands and PR template guidance for submitting changes.
10. [Changelog](Changelog.md) — Canonical changelog and recent release notes.
11. [Recent Changes](Recent-Changes.md) — Short summary of recent repo changes contributors should know about.
12. [Roadmap](Roadmap.md) — Project priorities and near-term goals.
13. [FAQ](FAQ.md) — Frequently asked questions and troubleshooting tips.

## How this page is used

- GitHub Pages: The `docs/` folder is published to GitHub Pages. `index.md` is the landing page used when the docs site is served from this folder.
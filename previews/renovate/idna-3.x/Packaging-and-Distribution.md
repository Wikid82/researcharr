Packaging and Distribution

This project aims to provide convenient distribution options once the core application and CI are stable. The goal of packaging is to make it simple for users to run `researcharr` without dealing with Python virtualenvs or Docker if they prefer native installs.

Target platforms and formats

- Linux: DEB, RPM, AppImage, Flatpak
- macOS: PKG, Homebrew formula / tap
- Windows: EXE (NSIS), MSI
- Container images: GHCR images are available for all published branches

When to produce packages

- Packaging work should begin after tests and CI are stable and the tool's runtime configuration is finalized.
- Start with Linux DEB/APPIMAGE for widest immediate reach and CI automation.

Recommended approach

1. Prepare reproducible build steps (Docker-based builders are recommended).
2. Write small CI jobs that build artifacts and attach them to releases, or publish to package repos (e.g., Homebrew tap, GitHub Releases, Debian repository).
3. Sign artifacts using a dedicated signing key for releases.

Example CI tasks to add (high-level)

- `ci/package-deb.yml` — Build a DEB package in a reproducible Docker environment and upload the artifact to GitHub Releases when a tag is pushed.
- `ci/package-appimage.yml` — Produce AppImage; useful for Linux desktop users.
- `ci/release.yml` — Orchestrates tagging, building, signing, and publishing packages and Docker images.

Notes about Docker images

- The repository builds and pushes GHCR images for branches. Images are tagged per-branch (e.g. `ghcr.io/wikid82/researcharr:development`) plus special branches (`latest`, `development`).
- CI currently uses caching for pip and Docker build layers. Adjust the publish rules if you want to disallow publishing from forks or PRs.

Security and reproducible builds

- Keep dependency versions pinned in `requirements.txt` for reproducible packaging.
- Use a dedicated signing key and protect it in CI secrets when signing release artifacts.

Next steps

If you'd like, I can draft the first `ci/package-deb.yml` workflow that:

- Uses a small Docker builder image (e.g., `python:3.X-slim`),
- Installs build dependencies,
- Assembles a minimal filesystem structure for the DEB,
- Builds a DEB and uploads it as a release artifact.

Ask if you want that prototype and which platform to target first.

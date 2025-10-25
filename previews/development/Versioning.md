# Versioning & Releases

This document provides detailed guidance for build metadata, CI tagging,
deployment best practices, and troubleshooting. The README contains a short
summary and example usage; this page contains the full reference for
maintainers and operators.

## What we publish

- Tags: CI publishes multiple tags for each successful build:
  - Semantic tag derived from `git describe --tags` when available (e.g. `1.2.3`).
  - Build-specific tag: `${VERSION}-build${BUILD_NUMBER}` (e.g. `1.2.3-build45`).
  - Short SHA tag: the first 8 chars of commit SHA (e.g. `abcdef12`).
  - Branch tags: the branch name and a `branch-<name>` tag for easier QA.

- OCI labels: images include these labels (set at build time):
  - `org.opencontainers.image.version` — the release/version string
  - `org.opencontainers.image.revision` — short git sha
  - `org.opencontainers.image.created` — UTC build datetime

- `/app/VERSION` file: the image includes a small file created at build
  time with key=value lines, for example:

```
version=1.2.3
build=45
sha=abcdef12
```

  The running application exposes the same values via `/api/version`.

## CI build & tagging (example)

In GitHub Actions, set these environment values before the Docker build:

```bash
VERSION=$(git describe --tags --dirty --always || echo "0.0.0")
BUILD_NUMBER=${GITHUB_RUN_NUMBER}
GIT_SHA=${GITHUB_SHA::8}
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

Then pass them to the Docker build as build args and tag multiple images. The
CI workflow should also capture and print the pushed image digest so support
can later correlate a running container with the pushed image.

## Runtime: how to identify the running image

Support and automated systems should collect:

- The output of the `/api/version` endpoint (JSON). This returns the
  values from `/app/VERSION` and is intended to be public/read-only.
- The container startup logs (the image metadata is logged on startup).
- The registry digest (printed by CI). The digest uniquely identifies the
  pushed image and should be provided in CI logs; deployments can pin by
  digest (recommended) using `image@sha256:...`.

## Injecting digest at runtime (optional)

If you want the running container logs to include the exact pushed digest,
configure your deployment to set an environment variable (for example
`IMAGE_DIGEST`) when starting the container. The app will log `IMAGE_DIGEST`
if present in the environment.

Example `docker-compose` snippet:

```yaml
services:
  researcharr:
    image: ghcr.io/wikid82/researcharr@sha256:<digest>
    environment:
      - IMAGE_DIGEST=sha256:<digest>
    volumes:
      - /path/to/config:/config
```

## Troubleshooting checklist for support

When a user reports an issue, ask for:

1. Output of `GET /api/version`.
2. The first 50 lines of container logs (startup lines include Image build info).
3. The registry tag or digest used to deploy the image (if available).

With these three pieces of data you can confirm whether the user's image
contains a fix or needs an update.

## Advanced: inspecting image manifests

Use `crane`, `skopeo`, or Docker registry API to inspect labels for a given
tag/digest. Example with `crane`:

```bash
crane manifest ghcr.io/wikid82/researcharr:1.2.3 | jq '.'
```

This will show labels and the manifest digest.

## Versioning policy notes

- Prefer semantic version tags for releases. Use build-specific tags for
  traceability between CI runs and pushed images.
- Keep the README concise; this document contains the full guidance.

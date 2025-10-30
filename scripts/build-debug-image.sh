#!/usr/bin/env bash
set -euo pipefail

# Build and optionally push the debug-target image.
# Usage:
#   ./scripts/build-debug-image.sh [-p] [-t TAG]
# Options:
#   -p    Push image to registry (requires DOCKER_PUSH=true or GHCR credentials configured)
#   -t TAG    Use TAG (default: researcharr:debug-local)

PUSH=0
TAG="researcharr:debug-local"

while getopts "pt:" opt; do
  case "$opt" in
    p) PUSH=1 ;;
    t) TAG="$OPTARG" ;;
    *) echo "Usage: $0 [-p] [-t TAG]"; exit 1 ;;
  esac
done

echo "Building debug image tag=$TAG"
docker build --progress=plain --target debug -t "$TAG" .

if [ "$PUSH" -eq 1 ]; then
  echo "Pushing $TAG"
  docker push "$TAG"
fi

echo "Done."

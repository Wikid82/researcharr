#!/usr/bin/env bash
# Collect debug artifacts for the 'researcharr' container.
# Produces a tar.gz in the current directory named researcharr-debug-<ts>.tar.gz

set -euo pipefail
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT=researcharr-debug-${TS}.tar.gz
TMPDIR=$(mktemp -d)
CONTAINER=${1:-researcharr}

echo "Collecting debug output for container: $CONTAINER"
cd "$TMPDIR"

# 1) docker inspect
if docker inspect "$CONTAINER" > inspect.json 2>/dev/null; then
  echo "wrote inspect.json"
else
  echo "container $CONTAINER not found or not running; continuing with available data"
fi

# 2) docker logs (both stdout & recent)
if docker logs --since 1h "$CONTAINER" > logs.last_hour.log 2>&1; then
  echo "wrote logs.last_hour.log"
else
  docker logs "$CONTAINER" > logs.full.log 2>&1 || true
  echo "wrote logs.full.log (fallback)"
fi

# 3) docker top
docker top "$CONTAINER" > docker_top.txt 2>/dev/null || true

# 4) docker ps -a
docker ps -a --filter "name=$CONTAINER" --no-trunc > docker_ps.txt || true

# 5) capture container filesystem bits if container exists
if docker inspect "$CONTAINER" >/dev/null 2>&1; then
  mkdir -p container-files
  # Copy /config contents if present
  docker cp "$CONTAINER":/config container-files/ 2>/dev/null || true
  # Copy app VERSION file if present
  docker cp "$CONTAINER":/app/VERSION container-files/ 2>/dev/null || true
fi

# 6) include local files that are useful
cp -a /etc/hosts container-etc-hosts 2>/dev/null || true

# 7) docker-compose logs (if using compose)
if command -v docker-compose >/dev/null 2>&1; then
  docker-compose logs > compose_logs.txt 2>&1 || true
fi
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  docker compose logs > compose_v2_logs.txt 2>&1 || true
fi

# 8) list the collected files and archive them
ls -la

tar czf "${OLDPWD}/${OUT}" . || true

echo "Created ${OUT} in ${OLDPWD}"

# cleanup
rm -rf "$TMPDIR"

# Print a short instruction about sharing
cat <<EOF

Debug bundle ready: ${OUT}
You can upload this file when opening an issue or share it privately.
If the container was running owned files (e.g., DB), check permissions before sharing.
EOF

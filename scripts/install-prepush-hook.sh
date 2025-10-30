#!/usr/bin/env bash
set -euo pipefail

# Installs a local git pre-push hook that runs the project's pytest wrapper.
# This avoids pre-commit re-running formatters/lint hooks during push-stage.

HOOK_PATH=".git/hooks/pre-push"
cat > "$HOOK_PATH" <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail

# Run the pytest wrapper; forward exit code so a failing test prevents push.
exec "$(pwd)/scripts/run-pytest-prepush.sh"
HOOK

chmod +x "$HOOK_PATH"
echo "Installed pre-push hook -> $HOOK_PATH"

#!/usr/bin/env bash
# Formats YAML files in the repository using Prettier.
set -euo pipefail
ROOT_DIR=$(dirname "$(dirname "$0")")
cd "$ROOT_DIR"
# Exclude virtualenvs and vendor directories
npx --yes prettier --write "**/*.{yml,yaml}" --ignore-path .gitignore
echo "Prettier formatting complete."

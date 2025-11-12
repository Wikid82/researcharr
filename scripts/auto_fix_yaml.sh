#!/usr/bin/env bash
# Auto-fix common YAML lint issues:
# - Prepend '---' document start when missing
# - Ensure at least two spaces before inline comments ("  #")
# Usage: run from repo root
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

echo "Finding tracked YAML files..."
mapfile -t files < <(git ls-files '*.yml' '*.yaml' | grep -vE '^(.venv/|.tox/|.venv|.tox)')
echo "Found ${#files[@]} YAML files"

modified=0
for f in "${files[@]}"; do
  # skip binary or large files
  [ -f "$f" ] || continue

  # Read first non-empty line
  first=$(awk 'NF{print; exit}' "$f" || true)
  tmpfile=$(mktemp)

  # Prepend document start if missing
  if [ -n "$first" ] && [ "${first:0:3}" != "---" ]; then
    printf '---\n' > "$tmpfile"
    cat "$f" >> "$tmpfile"
    mv "$tmpfile" "$f"
    echo "Prepended document start to $f"
    modified=$((modified+1))
  else
    rm -f "$tmpfile"
  fi

  # Normalize single-space before inline comments to two spaces
  # Only change occurrences of ' <single-space>#' to '  #' where there's one space before '#'
  # This is conservative: it won't touch comments at line start
  sed -E -i.bak 's/([^[:space:]]) #/\1  #/g' "$f" || true
  if ! cmp -s "$f" "$f.bak"; then
    rm -f "$f.bak"
    echo "Fixed comment spacing in $f"
    git add -- "$f"
    modified=$((modified+1))
  else
    rm -f "$f.bak"
  fi
done

if [ $modified -gt 0 ]; then
  git commit -m "chore: auto-fix YAML (docstart + comment spacing)" || true
  echo "Committed $modified changes"
else
  echo "No YAML changes required"
fi

if command -v pre-commit >/dev/null 2>&1; then
  echo "Running pre-commit hooks..."
  pre-commit run --all-files || true
  git add -A || true
  git commit -m "chore: apply pre-commit fixes for YAML" || echo "No pre-commit fixes to commit"
fi

echo "Re-running yamllint summary:"
yamllint -c .yamllint . | sed -n '1,200p' || true

echo "Done."

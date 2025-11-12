#!/usr/bin/env bash
# Auto-fix common YAML lint issues:
# - Prepend '---' document start when missing
# - Ensure at least two spaces before inline comments ("  #")
#
# Improvements in this version:
# - Skip files listed in .secrets.baseline (to avoid detect-secrets line-number churn)
# - Add --dry-run and --force flags
# - Safer commit flow: collect changes, show summary, commit once
# Usage: run from repo root

set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

DRY_RUN=0
FORCE=0
RUN_PRE_COMMIT=1

usage() {
  cat <<EOF
Usage: $(basename "$0") [--dry-run] [--force] [--no-pre-commit]
  --dry-run        Show what would change without writing files or committing
  --force          Force changes even for files present in .secrets.baseline
  --no-pre-commit  Don't run pre-commit hooks after changes
EOF
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --force) FORCE=1; shift ;;
    --no-pre-commit) RUN_PRE_COMMIT=0; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown arg: $1"; usage ;;
  esac
done

echo "Finding tracked YAML files..."
mapfile -t files < <(git ls-files '*.yml' '*.yaml' | grep -vE '^(\.venv/|\.tox/|\.venv|\.tox)')
echo "Found ${#files[@]} YAML files"

# Build exclude set from .secrets.baseline to avoid detect-secrets churn
declare -A exclude
if [ -f .secrets.baseline ]; then
  # Use Python to reliably parse JSON keys
  while IFS= read -r p; do
    exclude["$p"]=1
  done < <(python - <<'PY'
import json,sys
try:
    with open('.secrets.baseline') as f:
        data=json.load(f)
except Exception:
    sys.exit(0)
for k in data.keys():
    print(k)
PY
)
fi

# Always exclude these files by default
exclude[".yamllint"]=1
exclude[".pre-commit-config.yaml"]=1
exclude[".secrets.baseline"]=1

changed_files=()

for f in "${files[@]}"; do
  [ -f "$f" ] || continue

  if [ ${exclude["$f"]+0} ] && [ "$FORCE" -eq 0 ]; then
    echo "Skipping $f (listed in .secrets.baseline or excluded)"
    continue
  fi

  # Read first non-empty line
  first=$(awk 'NF{print; exit}' "$f" || true)

  # Work on a temp copy when doing dry-run so original is not modified
  if [ "$DRY_RUN" -eq 1 ]; then
    tmpfile=$(mktemp)
    cp -- "$f" "$tmpfile"
  else
    tmpfile=$(mktemp)
  fi

  modified_local=0

  # Prepend document start if missing
  if [ -n "$first" ] && [ "${first:0:3}" != "---" ]; then
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "[DRY-RUN] Would prepend document start to $f"
    else
      printf '%s\n' '---' > "$tmpfile"
      cat "$f" >> "$tmpfile"
      mv "$tmpfile" "$f"
      tmpfile=$(mktemp) # refresh tmpfile for next operation
      echo "Prepended document start to $f"
      modified_local=1
    fi
  fi

  # Normalize single-space before inline comments to two spaces
  if [ "$DRY_RUN" -eq 1 ]; then
    # Show a short diff for dry-run
    sed -E 's/([^[:space:]]) #/\1  #/g' "$f" | diff -u --label "$f (orig)" --label "$f (fixed)" - "$f" || true
  else
    sed -E -i.bak 's/([^[:space:]]) #/\1  #/g' "$f" || true
    if ! cmp -s "$f" "$f.bak"; then
      rm -f "$f.bak"
      echo "Fixed comment spacing in $f"
      modified_local=1
    else
      rm -f "$f.bak"
    fi
  fi

  if [ "$modified_local" -eq 1 ]; then
    changed_files+=("$f")
  fi
done

if [ ${#changed_files[@]} -eq 0 ]; then
  echo "No YAML changes required"
else
  echo "Files changed:"
  for cf in "${changed_files[@]}"; do echo " - $cf"; done

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "Dry-run mode: not staging or committing changes"
  else
    git add -- "${changed_files[@]}"
    git commit -m "chore: auto-fix YAML (docstart + comment spacing)" || true
    echo "Committed ${#changed_files[@]} file(s)"
  fi
fi

if [ "$RUN_PRE_COMMIT" -eq 1 ] && [ "$DRY_RUN" -eq 0 ]; then
  if command -v pre-commit >/dev/null 2>&1; then
    echo "Running pre-commit hooks..."
    pre-commit run --all-files || true
    git add -A || true
    git commit -m "chore: apply pre-commit fixes for YAML" || echo "No pre-commit fixes to commit"
  else
    echo "pre-commit not available; skipping hooks"
  fi
fi

echo "Re-running yamllint summary:"
yamllint -c .yamllint . | sed -n '1,200p' || true

echo "Done."

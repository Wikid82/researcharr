#!/usr/bin/env bash
set -euo pipefail

# Cleanup Renovate branches that contain malformed/overlong filenames.
#
# Usage:
#   ./scripts/cleanup-renovate-branches.sh            # dry run (no deletions)
#   ./scripts/cleanup-renovate-branches.sh --apply    # actually delete offending remote branches
#
# Details:
# - Enumerates remote branches matching origin/renovate/*
# - For each branch, checks for:
#   * path components > 120 chars, or
#   * suspicious characters (quotes/newlines) suggesting accidental filenames
# - In dry-run, prints candidates; with --apply, deletes them from origin.

APPLY=0
if [[ ${1:-} == "--apply" ]]; then
  APPLY=1
fi

# Ensure we have up-to-date refs
git fetch origin --prune

mapfile -t RENOVATE_BRANCHES < <(git for-each-ref --format='%(refname:short)' refs/remotes/origin/renovate/)

if [[ ${#RENOVATE_BRANCHES[@]} -eq 0 ]]; then
  echo "No origin/renovate/* branches found." >&2
  exit 0
fi

echo "Scanning ${#RENOVATE_BRANCHES[@]} Renovate branches for malformed filenames..." >&2

PROBLEM_COUNT=0
for rref in "${RENOVATE_BRANCHES[@]}"; do
  # Strip 'origin/' prefix to construct the branch name
  bname=${rref#origin/}

  # List files in the tree
  # shellcheck disable=SC2016
  files=$(git ls-tree -r --name-only "$rref" || true)
  if [[ -z "$files" ]]; then
    continue
  fi

  offending=()
  while IFS= read -r f; do
    # Check path components for length and suspicious edge quotes/newlines
    IFS='/' read -r -a comps <<< "$f"
    bad=0
    for comp in "${comps[@]}"; do
      # component too long
      if (( ${#comp} > 120 )); then
        bad=1; break
      fi
      # suspicious characters
      if printf '%s' "$comp" | grep -Eq '^["'"'`]|["'"'`]$|[\n\r\t]|\\{8,}'; then
        bad=1; break
      fi
    done
    if (( bad == 1 )); then
      offending+=("$f")
    fi
  done <<< "$files"

  if (( ${#offending[@]} > 0 )); then
    ((PROBLEM_COUNT++))
    echo "- Branch $bname has ${#offending[@]} offending paths (showing up to 5):"
    printf '    %s\n' "${offending[@]:0:5}"
    if (( APPLY == 1 )); then
      echo "  Deleting remote branch: $bname"
      git push origin --delete "$bname" || true
    fi
  fi

done

if (( PROBLEM_COUNT == 0 )); then
  echo "No malformed filenames found in Renovate branches." >&2
else
  if (( APPLY == 1 )); then
    echo "Deleted $PROBLEM_COUNT Renovate branches with malformed filenames." >&2
  else
    echo "Found $PROBLEM_COUNT offending Renovate branches. Re-run with --apply to delete." >&2
  fi
fi

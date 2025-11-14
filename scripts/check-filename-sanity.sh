#!/usr/bin/env bash
# Pre-commit hook to validate that filenames are sane:
# - No quotes, newlines, or other control characters
# - Path components under 200 characters (to avoid filesystem limits)

set -euo pipefail

EXIT_CODE=0

# Get list of files being committed
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    AGAINST=HEAD
else
    # Initial commit: diff against an empty tree object
    AGAINST=$(git hash-object -t tree /dev/null)
fi

# Check all files in the staging area
while IFS= read -r -d '' file; do
    # Check for quotes, newlines, control characters
    if [[ "$file" =~ [\"\'$'\n'$'\r'$'\t'] ]]; then
        echo "ERROR: File path contains invalid characters (quotes/newlines/control): $file" >&2
        EXIT_CODE=1
        continue
    fi

    # Check each path component length
    IFS='/' read -ra COMPONENTS <<< "$file"
    for component in "${COMPONENTS[@]}"; do
        if [[ ${#component} -gt 200 ]]; then
            echo "ERROR: Path component exceeds 200 characters: $component (in $file)" >&2
            EXIT_CODE=1
            break
        fi
    done
done < <(git diff --cached --name-only --diff-filter=ACMR -z "$AGAINST")

if [[ $EXIT_CODE -ne 0 ]]; then
    echo "" >&2
    echo "Commit rejected: filenames contain invalid characters or are too long." >&2
    echo "Please rename the files and try again." >&2
fi

exit $EXIT_CODE

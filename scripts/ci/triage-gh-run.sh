#!/usr/bin/env bash
# Triages a GitHub Actions run by downloading and summarizing test logs and artifacts
# Usage: ./scripts/ci/triage-gh-run.sh <run-id> [owner/repo]
# Example: ./scripts/ci/triage-gh-run.sh 19345196475 Wikid82/researcharr

set -euo pipefail

if [[ -z "${1:-}" ]]; then
  echo "Usage: $0 <run-id> [owner/repo]"
  exit 1
fi
RUN_ID=$1
REPO=${2:-Wikid82/researcharr}
OUT_DIR=./actions-artifacts/run-${RUN_ID}
mkdir -p "$OUT_DIR"

echo "Downloading run artifacts for $RUN_ID into $OUT_DIR..."
if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI is required. Install and authenticate (https://cli.github.com/manual/installation)"
  exit 2
fi

echo "Running: gh run download $RUN_ID --repo $REPO --dir $OUT_DIR"
gh run download "$RUN_ID" --repo "$REPO" --dir "$OUT_DIR"

# Make a working folder with extracted logs
LOG_DIR="$OUT_DIR/logs"
mkdir -p "$LOG_DIR"

# Move test log artifacts into logs (if zipped, unzip them)
for f in "$OUT_DIR"/*; do
  case "$f" in
    (*.zip)
      echo "Unzipping $f"
      unzip -q "$f" -d "$OUT_DIR/tmp-unzip-$(basename "$f")" || true
      ;;
    (*)
      # If file is a test results log or test-*zip, copy
      if [[ "$(basename "$f")" == test-logs-* ]]; then
        # if it's a directory, copy its contents
        if [[ -d "$f" ]]; then
          cp -R "$f"/* "$LOG_DIR/" 2>/dev/null || true
        else
          # If a file, copy it to the log dir
          cp "$f" "$LOG_DIR/" 2>/dev/null || true
        fi
      fi
      ;;
  esac
done

# Also find any extracted files
find "$OUT_DIR" -type f -name "test-results.log" -exec cp -v {} "$LOG_DIR/" \; || true

echo "Collected logs in $LOG_DIR"

# Summary search patterns
PATTERN='FAILED|Traceback|ERROR|AssertionError|Process completed with exit code 1|FAILED\s+tests/'

# Print summary header
printf "\n*** Summary of failures from run %s ***\n\n" "$RUN_ID"

# grep across logs, show file:line:context
if ls "$LOG_DIR"/* &>/dev/null; then
  grep -nE "$PATTERN" "$LOG_DIR"/* || true
else
  echo "No log files found under $LOG_DIR"
fi

# Show failing pytest summaries
printf "\n*** Pytest failing sums (grep for 'FAILED' or 'FAILED tests/') ***\n\n"
for file in "$LOG_DIR"/*; do
  echo "-- $file --"
  grep -nE "FAILED [^\n]*" "$file" | sed -n '1,200p' || true
  grep -nE "E\s+" "$file" | sed -n '1,40p' || true
done

# Provide an artifact summary (wheelhouse contents)
printf "\n*** Wheelhouse artifact summary ***\n\n"
for w in "$OUT_DIR"/*wheelhouse*; do
  echo "-- $w --"
  if [[ -f "$w" ]] && file "$w" | grep -qi 'Zip archive data'; then
    unzip -l "$w" | sed -n '1,200p'
  elif [[ -d "$w" ]]; then
    ls -la "$w" | sed -n '1,200p'
  fi
done

# Optional: diff 3.10 logs vs failing versions
printf "\n*** Compare 3.10 vs other Python versions ***\n\n"
BASE="$LOG_DIR/test-results-3.10.log"
if [[ -f "$BASE" ]]; then
  for p in 3.11 3.12 3.13 3.14; do
    FILE="$LOG_DIR/test-results-${p}.log"
    if [[ -f "$FILE" ]]; then
      printf "--- Diff 3.10 vs %s ---\n" "$p"
      diff -u "$BASE" "$FILE" | sed -n '1,200p' || true
    fi
  done
else
  echo "No 3.10 baseline log found at $BASE, skipping diffs"
fi

printf "\n*** End of triage script. Logs are under: $OUT_DIR/logs ***\n"

exit 0

#!/usr/bin/env bash
set -euo pipefail

export RESEARCHARR_DISABLE_PLUGINS=${RESEARCHARR_DISABLE_PLUGINS:-1}
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=${PYTEST_DISABLE_PLUGIN_AUTOLOAD:-1}
export PYTEST_ADDOPTS=${PYTEST_ADDOPTS:-}

echo "Preparing container environment..."
apt-get update -qq >/dev/null
apt-get install -y git >/dev/null
python -m pip install --upgrade pip >/dev/null
python -m pip install -q --no-input -r requirements.txt -r requirements-dev.txt
git config --global --add safe.directory /work

mkdir -p artifacts
OUT_DIR=${OUT_DIR:-/tmp/researcharr-bisect}
mkdir -p "$OUT_DIR"

readarray -t files < <(find tests -type f -name 'test_*.py' | sort)
echo "Found ${#files[@]} test files"

for i in $(seq 1 10); do
  echo -e "\n=== RUN $i ==="
    if RESEARCHARR_DISABLE_PLUGINS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS= \
      pytest --override-ini=addopts= -p no:xdist --junit-xml="$OUT_DIR/junit_${i}.xml" --maxfail=1 --disable-warnings tests/; then
    echo "run $i passed"
  else
    echo "run $i FAILED"
    cp artifacts/junit_${i}.xml artifacts/last_failed_junit.xml || true
    echo "Starting bisect to find minimal failing test file..."

    n=${#files[@]}
    left=0
    right=$((n-1))
    while [ $left -lt $right ]; do
      mid=$(( (left+right)/2 ))
      # build subset array from left..mid
      subset=( "${files[@]:left:mid-left+1}" )
       echo "Testing subset $left..$mid (${#subset[@]} files)"
       if RESEARCHARR_DISABLE_PLUGINS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS= \
         pytest --override-ini=addopts= -p no:xdist --junit-xml="$OUT_DIR/bisect_run.xml" --maxfail=1 --disable-warnings "${subset[@]}"; then
        echo "subset $left..$mid PASSED -> moving right"
        left=$((mid+1))
      else
        echo "subset $left..$mid FAILED -> narrowing"
        right=$mid
      fi
    done

    culprit=${files[$left]}
    echo "Identified culprit file: $culprit"
    echo "Running full file to capture failing test(s)"
    RESEARCHARR_DISABLE_PLUGINS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS= \
      pytest --override-ini=addopts= -p no:xdist -vv --junit-xml="$OUT_DIR/bisect_final.xml" --maxfail=1 --disable-warnings "$culprit" || true
    echo "Bisect done, artifacts saved under $OUT_DIR"
    # keep exit non-zero to signal caller if desired; exit gracefully 0 to allow container to finish
    exit 0
  fi
done

echo "All 10 runs passed"

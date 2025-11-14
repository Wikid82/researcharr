#!/usr/bin/env bash
set -euo pipefail

culprit=${1:-tests/webui/test_webui_shim_runtime.py}
export RESEARCHARR_DISABLE_PLUGINS=${RESEARCHARR_DISABLE_PLUGINS:-1}
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=${PYTEST_DISABLE_PLUGIN_AUTOLOAD:-1}
export PYTEST_ADDOPTS=${PYTEST_ADDOPTS:-}
echo "Culprit: $culprit"

mkdir -p artifacts/pairwise

# writable tmp output dir for junit/stderr
OUT_DIR=${OUT_DIR:-/tmp/researcharr-bisect}
mkdir -p "$OUT_DIR"

# If a nodeid-style culprit was passed (e.g. tests/foo.py::test_bar),
# keep the nodeid in `culprit_nodeid` and map the file portion to `culprit_file`.
culprit_nodeid=""
culprit_file="$culprit"
if [[ "$culprit" == *"::"* ]]; then
  culprit_nodeid="$culprit"
  culprit_file="${culprit%%::*}"
fi

# If the culprit file doesn't exist exactly as provided, try to locate it
if [ ! -f "$culprit_file" ]; then
  # try to find a matching file under tests/ that ends with the same path
  match=$(find tests -type f -name "$(basename "$culprit_file")" | head -n1 || true)
  if [ -n "$match" ]; then
    culprit_file="$match"
    # if we had a nodeid, rebuild the nodeid with the discovered path
    if [ -n "$culprit_nodeid" ]; then
      culprit_nodeid="$culprit_file::${culprit#*::}"
    fi
  else
    echo "Culprit file not found: $culprit_file" >&2
    exit 1
  fi
fi

readarray -t files < <(find tests -type f -name 'test_*.py' | sort)
echo "Total test files: ${#files[@]}"

# Build list of other files excluding culprit
others=()
for f in "${files[@]}"; do
  if [ "$f" != "$culprit" ]; then
    others+=("$f")
  fi
done

if [ ${#others[@]} -eq 0 ]; then
  echo "No other test files to pair with; exiting"
  exit 0
fi

echo "Starting binary search to find interacting file (culprit + subset)"
n=${#others[@]}
left=0
right=$((n-1))
found_pair=""
while [ $left -lt $right ]; do
  mid=$(( (left+right)/2 ))
  subset=( "${others[@]:left:mid-left+1}" )
    echo "Testing culprit + subset $left..$mid (${#subset[@]} files)"
    # use override-ini to avoid pyproject addopts; write junit to a writable location
    run_args=(--override-ini=addopts= -p no:xdist --junit-xml="$OUT_DIR/pairwise_bisect_run.xml" --maxfail=1 --disable-warnings)
    # choose whether to pass a nodeid or a file path for the culprit
    if [ -n "$culprit_nodeid" ]; then
      py_args=("$culprit_nodeid" "${subset[@]}")
    else
      py_args=("$culprit_file" "${subset[@]}")
    fi
    if RESEARCHARR_DISABLE_PLUGINS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS= \
      pytest "${run_args[@]}" "${py_args[@]}" 2>"$OUT_DIR/pairwise_bisect_run.stderr"; then
    echo "subset $left..$mid PASSED -> move right"
    left=$((mid+1))
  else
    echo "subset $left..$mid FAILED -> narrowing"
    right=$mid
    found_pair=1
  fi
done

candidate=${others[$left]}
echo "Candidate interacting file: $candidate"
echo "Running culprit + candidate to confirm"
final_run_args=(--override-ini=addopts= -p no:xdist --junit-xml="$OUT_DIR/pairwise_bisect_final.xml" --maxfail=1 --disable-warnings)
if [ -n "$culprit_nodeid" ]; then
  final_py_args=("$culprit_nodeid" "$candidate")
else
  final_py_args=("$culprit_file" "$candidate")
fi
if RESEARCHARR_DISABLE_PLUGINS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS= \
  pytest "${final_run_args[@]}" "${final_py_args[@]}" 2>"$OUT_DIR/pairwise_bisect_final.stderr"; then
  echo "culprit + candidate passed — binary search did not find a deterministic interacting file"
else
  echo "Found interacting pair: $culprit + $candidate";
  exit 0
fi

echo "Binary search did not find interacting pair. Running randomized-order stress runs (will try 50 iterations)."
iters=${2:-50}
for i in $(seq 1 $iters); do
  echo "Random run $i"
  # shuffle full file list to change execution order
  printf "%s
" "${files[@]}" | shuf > /tmp/shuffled_files.txt
  mapfile -t shuffled < /tmp/shuffled_files.txt
  run_args_rand=(--override-ini=addopts= -p no:xdist -q --junit-xml="$OUT_DIR/random_${i}.xml" --maxfail=1 --disable-warnings)
  if RESEARCHARR_DISABLE_PLUGINS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_ADDOPTS= \
    pytest "${run_args_rand[@]}" "${shuffled[@]}" 2>"$OUT_DIR/random_${i}.stderr"; then
      echo "random $i passed"
    else
      echo "random $i FAILED; artifacts saved under $OUT_DIR/"
      exit 0
  fi
done

echo "Randomized runs completed with no failures"
exit 0

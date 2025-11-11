#!/usr/bin/env python3
"""Collect tests and run them one-by-one to find a hanging test.

Usage: run from repo root with the project's venv (the task will run it).
"""

import shlex
import subprocess
import sys

PYTEST = sys.executable + " -m pytest"
TIMEOUT = 60  # seconds per test


def collect_tests():
    print("Collecting tests...")
    proc = subprocess.run(
        shlex.split(PYTEST + " --collect-only -q tests/"),
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print("pytest --collect-only failed:\n", proc.stdout, proc.stderr)
        sys.exit(proc.returncode)
    nodeids = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    print(f"Collected {len(nodeids)} tests")
    return nodeids


def run_test(nodeid):
    cmd = shlex.split(PYTEST + " -q " + shlex.quote(nodeid))
    print("\n=== Running:", nodeid)
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=TIMEOUT)
        print(proc.stdout)
        if proc.returncode == 0:
            print("RESULT: PASS")
            return "pass"
        else:
            print(proc.stdout)
            print(proc.stderr)
            print("RESULT: FAIL (exit code", proc.returncode, ")")
            return "fail"
    except subprocess.TimeoutExpired as e:
        print("--- TIMEOUT after", TIMEOUT, "seconds ---")
        # Print any captured output
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return "timeout"


def main():
    nodeids = collect_tests()
    for n in nodeids:
        res = run_test(n)
        if res == "timeout":
            print("\nHANGING TEST IDENTIFIED:", n)
            sys.exit(2)
    print("\nAll tests completed individually without timing out.")


if __name__ == "__main__":
    main()

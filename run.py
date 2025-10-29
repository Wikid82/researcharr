#!/usr/bin/env python3
"""Shim run.py that delegates to `scripts/run.py`.

This lightweight wrapper keeps compatibility for any tooling that invokes
`/app/run.py` while centralizing the executable implementation under
`/app/scripts/run.py`.
"""
import os
import sys

if __name__ == "__main__":
    # Exec the canonical script under /app/scripts so the process becomes PID 1
    os.execv(sys.executable, [sys.executable, "/app/scripts/run.py"])

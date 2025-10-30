#!/usr/bin/env python3
"""Compatibility shim: re-export the package `researcharr.run` implementation.

Some consumers import the top-level `run` module; make sure it exposes the
same public names as `researcharr.run` by importing and re-exporting them.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

# Import the package implementation and rebind public symbols so imports of
# the top-level `run` module remain compatible.
_impl = import_module("researcharr.run")

# Re-export commonly used names
run_job = getattr(_impl, "run_job")
main = getattr(_impl, "main")
LOG_PATH = getattr(_impl, "LOG_PATH")
SCRIPT = getattr(_impl, "SCRIPT")

if __name__ == "__main__":
    # Delegate CLI execution to the package implementation
    main()

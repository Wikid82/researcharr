#!/usr/bin/env python3
import importlib
import importlib.util
import os
import sys

print("PYTHONPATH:", os.environ.get("PYTHONPATH"))
print("sys.path:", sys.path)
print("cwd:", os.getcwd())
try:
    print("find_spec:", importlib.util.find_spec("researcharr"))
except Exception as e:
    print("find_spec failed:", e)
try:
    import researcharr

    print("researcharr __file__", getattr(researcharr, "__file__", None))
except Exception as e:
    print("import researcharr failed:", e)
try:
    import researcharr.db as rdb

    print("researcharr.db __file__", getattr(rdb, "__file__", None))
except Exception as e:
    print("import researcharr.db failed:", e)

if __name__ == "__main__":
    # Additional printouts when invoked directly
    try:
        spec = importlib.util.find_spec("researcharr")
        print("importlib spec:", spec)
        if spec is not None:
            print("loader:", getattr(spec, "loader", None))
    except Exception:
        pass

#!/usr/bin/env python3
import sys
import importlib
import os

print('PYTHONPATH:', os.environ.get('PYTHONPATH'))
print('sys.path:', sys.path)
print('cwd:', os.getcwd())
try:
    print('find_spec:', importlib.util.find_spec('researcharr'))
except Exception as e:
    print('find_spec failed:', e)
try:
    import researcharr
    print('researcharr __file__', getattr(researcharr, '__file__', None))
except Exception as e:
    print('import researcharr failed:', e)
try:
    import researcharr.db as rdb
    print('researcharr.db __file__', getattr(rdb, '__file__', None))
except Exception as e:
    print('import researcharr.db failed:', e)

if __name__ == '__main__':
    # Additional printouts when invoked directly
    try:
        import pkgutil
        print('pkgutil find:', pkgutil.get_loader('researcharr'))
    except Exception:
        pass

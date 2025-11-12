import os
import json
import logging
from prometheus_client import core

OUT_DIR = '/tmp/researcharr-bisect/logsnap'
os.makedirs(OUT_DIR, exist_ok=True)


def _snapshot_state():
    mgr = logging.root.manager
    logger_dict = {}
    try:
        items = list(mgr.loggerDict.items())
    except Exception:
        items = []
    for name, logger in items:
        try:
            logger_dict[name] = {
                'type': type(logger).__name__,
                'handlers': [type(h).__name__ for h in getattr(logger, 'handlers', [])],
                'level': getattr(logger, 'level', None),
                'propagate': getattr(logger, 'propagate', None),
            }
        except Exception as e:
            logger_dict[name] = {'error': str(e)}

    prom = []
    try:
        reg = core.REGISTRY
        if hasattr(reg, '_collector_to_names'):
            prom = [type(c).__name__ for c in getattr(reg, '_collector_to_names').keys()]
        elif hasattr(reg, 'collectors'):
            prom = [type(c).__name__ for c in getattr(reg, 'collectors')]
        else:
            prom = [repr(reg)]
    except Exception as e:
        prom = [f'ERR:{e}']

    return {'loggerDict_sample': dict(list(logger_dict.items())[:200]), 'prometheus': prom}


def _write(nodeid, stage, data):
    safe = nodeid.replace('::', '__').replace('/', '_')
    path = os.path.join(OUT_DIR, f'{stage}_{safe}.json')
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass


def pytest_runtest_setup(item):
    _write(item.nodeid, 'pre', _snapshot_state())


def pytest_runtest_teardown(item, nextitem):
    _write(item.nodeid, 'post', _snapshot_state())

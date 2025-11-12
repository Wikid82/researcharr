import logging
import os
import pathlib
import sys
import traceback

try:
    from prometheus_client import core as prom_core
except Exception:
    prom_core = None

import researcharr


OUTDIR = pathlib.Path("/tmp/researcharr-bisect")
OUTDIR.mkdir(parents=True, exist_ok=True)


def _safe_repr(obj):
    try:
        return repr(obj)
    except Exception:
        return f"<unreprable {type(obj).__name__}>"


def dump_logger_state(fp):
    lm = logging.root.manager
    root = logging.getLogger()
    cron = logging.getLogger("researcharr.cron")

    fp.write("=== logging root/info ===\n")
    fp.write(f"root.handlers={len(root.handlers)}\n")
    fp.write(f"root.level={root.level}\n")
    fp.write("\n")

    fp.write("=== researcharr.cron ===\n")
    try:
        fp.write(f"cron.handlers={len(cron.handlers)}\n")
        fp.write(f"cron.level={cron.level}\n")
        fp.write(f"cron.propagate={cron.propagate}\n")
        fp.write(f"cron.filters={len(getattr(cron, 'filters', []) or [])}\n")
    except Exception:
        fp.write("cron: could not inspect logger\n")
        traceback.print_exc(file=fp)
    fp.write("\n")

    fp.write("=== logging.manager.loggerDict (summary) ===\n")
    try:
        names = sorted(lm.loggerDict.keys())
        fp.write(f"logger_count={len(names)}\n")
        # print first/last 50 names to avoid extreme verbosity
        for name in names[:200]:
            entry = lm.loggerDict[name]
            entry_type = type(entry).__name__
            fp.write(f"{name}: {entry_type} {getattr(entry, 'level', '')} handlers={getattr(entry, 'handlers', None)} propagate={getattr(entry, 'propagate', '')}\n")
    except Exception:
        fp.write("could not dump loggerDict\n")
        traceback.print_exc(file=fp)
    fp.write("\n")


def dump_prometheus_state(fp):
    fp.write("=== prometheus client ===\n")
    if prom_core is None:
        fp.write("prometheus_client not available\n\n")
        return
    try:
        reg = prom_core.REGISTRY
        fp.write(f"REGISTRY: {type(reg).__name__} repr={_safe_repr(reg)}\n")
        # try to collect metrics (may be empty)
        try:
            collected = list(reg.collect())
            fp.write(f"collected_count={len(collected)}\n")
        except Exception as e:
            fp.write(f"collect() raised: {e!r}\n")
    except Exception:
        fp.write("error inspecting prometheus registry\n")
        traceback.print_exc(file=fp)
    fp.write("\n")


def dump_researcharr_module_state(fp):
    fp.write("=== researcharr module summary ===\n")
    try:
        attrs = [a for a in dir(researcharr) if not a.startswith("__")]
        fp.write(f"attr_count={len(attrs)}\n")
        for name in sorted(attrs):
            try:
                val = getattr(researcharr, name)
                fp.write(f"{name}: {type(val).__name__} {_safe_repr(val)[:200]}\n")
            except Exception:
                fp.write(f"{name}: <error getting attr>\n")
    except Exception:
        fp.write("error dumping researcharr module\n")
        traceback.print_exc(file=fp)
    fp.write("\n")


def write_diagnostics(name):
    path = OUTDIR / f"diagnostics_{name}.log"
    with path.open("w", encoding="utf-8") as fp:
        fp.write(f"PID={os.getpid()} python={sys.executable}\n")
        fp.write("\n")
        dump_logger_state(fp)
        dump_prometheus_state(fp)
        dump_researcharr_module_state(fp)


def test_diagnostics_clean_session():
    """Run this in a clean pytest session and save diagnostics."""
    write_diagnostics("clean")


def test_diagnostics_after_predecessor():
    """Run this after the identified predecessor test and save diagnostics."""
    write_diagnostics("after_predecessor")
import logging
import inspect
from prometheus_client import core


def dump_logger_info(logger):
    try:
        handlers = [type(h).__name__ for h in logger.handlers]
    except Exception:
        handlers = repr(getattr(logger, 'handlers', None))
    try:
        filters = [type(f).__name__ for f in logger.filters]
    except Exception:
        filters = repr(getattr(logger, 'filters', None))
    return {
        'name': logger.name,
        'level': logging.getLevelName(logger.level),
        'propagate': getattr(logger, 'propagate', None),
        'handlers': handlers,
        'filters': filters,
    }


def dump_manager_sample(limit=100):
    mgr = logging.root.manager
    out = {}
    try:
        items = list(mgr.loggerDict.items())
    except Exception:
        return {'error': 'unable to read loggerDict'}
    for name, logger in items[:limit]:
        try:
            out[name] = {
                'type': type(logger).__name__,
                'has_handlers': bool(getattr(logger, 'handlers', None)),
                'level': getattr(logger, 'level', '<no>'),
            }
        except Exception as e:
            out[name] = {'error': str(e)}
    return out


def dump_prometheus_registry():
    reg = core.REGISTRY
    collectors = []
    # Try common internal structures, but be defensive
    try:
        if hasattr(reg, '_collector_to_names'):
            for c in getattr(reg, '_collector_to_names').keys():
                collectors.append(type(c).__name__)
        elif hasattr(reg, 'collectors'):
            for c in getattr(reg, 'collectors'):
                collectors.append(type(c).__name__)
        else:
            collectors.append(repr(reg))
    except Exception as e:
        collectors.append(f'ERR:{e}')
    return {'registry_type': type(reg).__name__, 'collectors_sample': collectors[:50]}


def print_block(title, obj):
    print('\n' + '=' * 10 + f' {title} ' + '=' * 10)
    if isinstance(obj, dict):
        for k, v in list(obj.items())[:200]:
            print(f'{k}: {v}')
    else:
        print(obj)
    print('\n')


def test_dump_all():
    import researcharr

    root = logging.getLogger()
    cron = logging.getLogger('researcharr.cron')

    print_block('ROOT LOGGER', dump_logger_info(root))
    print_block('RESEARCHARR.CRON', dump_logger_info(cron))
    print_block('LOGGER MANAGER SAMPLE', dump_manager_sample(limit=200))
    print_block('PROMETHEUS REGISTRY', dump_prometheus_registry())

    # Dump a small sample of module-level callables on researcharr for potential monkeypatches
    sample = {}
    for name, val in inspect.getmembers(researcharr):
        if name.startswith('_'):
            continue
        if inspect.isfunction(val) or inspect.ismodule(val) or inspect.isclass(val):
            sample[name] = type(val).__name__
    print_block('RESEARCHARR ATTRS SAMPLE', sample)

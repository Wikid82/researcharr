import logging
import pathlib
import sys

OUT = pathlib.Path("/tmp/researcharr-bisect")
OUT.mkdir(parents=True, exist_ok=True)


def _repr_handler(h):
    return f"{type(h).__name__} level={getattr(h, 'level', None)} filters={len(getattr(h, 'filters', []) or [])} formatter={getattr(h, 'formatter', None)}"


def test_dump_handler_details():
    out = OUT / "handler_detail_after.log"
    with out.open("w") as f:
        f.write(f"python={sys.executable}\n")
        f.write(f"logging.disable={logging.disable}\n")
        f.write(f"logging.raiseExceptions={logging.raiseExceptions}\n")
        root = logging.getLogger()
        f.write(f"root.level={root.level}\n")
        f.write(f"root.handlers_count={len(root.handlers)}\n")
        for i, h in enumerate(root.handlers):
            f.write(f"root.handler[{i}]={_repr_handler(h)}\n")
        cron = logging.getLogger("researcharr.cron")
        f.write(
            f"researcharr.cron.level={cron.level} propagate={cron.propagate} disabled={cron.disabled}\n"
        )
        f.write(f"researcharr.cron.handlers_count={len(cron.handlers)}\n")
        for i, h in enumerate(cron.handlers):
            f.write(f"cron.handler[{i}]={_repr_handler(h)}\n")
        f.write("\nlogging.manager.loggerDict keys:\n")
        for k in sorted(logging.root.manager.loggerDict.keys()):
            f.write(f"{k}\n")

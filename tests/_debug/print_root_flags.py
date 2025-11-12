import logging


def test_print_root_flags():
    root = logging.getLogger()
    print("ROOT.handlers:", [type(h).__name__ for h in getattr(root, "handlers", [])])
    print("ROOT.level:", root.level)
    print("ROOT.propagate:", getattr(root, "propagate", None))
    print("ROOT.disabled:", getattr(root, "disabled", None))
    print("logging.raiseExceptions:", getattr(logging, "raiseExceptions", None))
    print("logging.lastResort:", getattr(logging, "lastResort", None))
    try:
        print("logging.manager.disable:", getattr(logging.root.manager, "disable", None))
    except Exception as e:
        print("logging.manager.disable: ERR", e)
    print("loggerDict count:", len(getattr(logging.root.manager, "loggerDict", {})))

import os

# Extend this package's __path__ to include the repository's top-level
# `plugins/` directory so imports like `researcharr.plugins.registry` will
# resolve to files in ../plugins without moving code.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TOP_LEVEL_PLUGINS = os.path.join(ROOT, "plugins")
if os.path.isdir(TOP_LEVEL_PLUGINS) and TOP_LEVEL_PLUGINS not in __path__:
    __path__.insert(0, TOP_LEVEL_PLUGINS)

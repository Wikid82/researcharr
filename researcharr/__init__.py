"""Compatibility package shim.

This project historically exposes a top-level module layout (e.g. factory.py,
researcharr.py, plugins/*). Tests and some consumers import `researcharr.*`.

To allow `import researcharr.plugins` and `import researcharr.factory` without
restructuring the repository, this package provides lightweight shims that
redirect imports to the existing top-level modules and plugins directory.
"""

# Expose a minimal package namespace; individual submodules are provided as
# small wrapper modules under the same package.
"""Compatibility package shim.

This package exposes the real top-level module implementation as
``researcharr.researcharr`` by loading the on-disk ``researcharr.py`` and
inserting it into sys.modules under the package submodule name. Tests and
consumers use ``from researcharr import researcharr as app``; providing the
loaded module as the attribute ``researcharr`` on the package ensures that
import-time lookups and patching behave consistently.
"""

from typing import Optional
import importlib.util
import os
import sys

__all__ = []


# Candidate locations for the implementation module. We check the current
# working directory first (test runners often run from the repo root), then
# fall back to paths relative to this package directory.
TOP_LEVEL: Optional[str] = None
# Try several candidate locations where the implementation may live. Tests and
# different run contexts may execute with different working directories, so
# include both cwd-based and package-relative locations.
candidates = [
	os.path.join(os.getcwd(), "researcharr.py"),
	os.path.abspath(os.path.join(os.path.dirname(__file__), "researcharr.py")),
	os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "researcharr.py")),
	os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "researcharr.py")),
	os.path.abspath(os.path.join(os.path.dirname(__file__), "researcharr", "researcharr.py")),
]
for c in candidates:
	if os.path.isfile(c):
		TOP_LEVEL = c
		break
# If not found yet, walk up a few directory levels from the package dir to
# look for a top-level `researcharr.py`. This covers several CI/test layouts.
if not TOP_LEVEL:
	base = os.path.dirname(__file__)
	for depth in range(1, 6):
		candidate = os.path.abspath(os.path.join(base, *([".."] * depth), "researcharr.py"))
		if os.path.isfile(candidate):
			TOP_LEVEL = candidate
			break


researcharr = None
if TOP_LEVEL:
	spec = importlib.util.spec_from_file_location("researcharr.researcharr", TOP_LEVEL)
	if spec and spec.loader:
		mod = importlib.util.module_from_spec(spec)
		# Execute the implementation module in its own namespace.
		spec.loader.exec_module(mod)  # type: ignore[arg-type]

		# Ensure the loaded module is available under the expected package
		# submodule name so callers and monkeypatching can target
		# "researcharr.researcharr" reliably.
		sys.modules["researcharr.researcharr"] = mod
		researcharr = mod
		__all__ = []

		# Prefer the normal import path first. This keeps imports deterministic in
		# most environments (including CI and local development). If that import
		# fails (unusual layouts), fall back to a file-based loader that locates the
		# top-level implementation by path.
		researcharr = None
		try:
			# Normal package-style import is the most explicit and maintainable.
			import importlib

			researcharr = importlib.import_module("researcharr.researcharr")
			# If the imported submodule doesn't expose expected implementation
			# attributes (this can happen when a lightweight shim/package is
			# present), treat it as not-loadable and fall back to the file-based
			# loader below.
			if not (hasattr(researcharr, "init_db") or hasattr(researcharr, "create_metrics_app")):
				researcharr = None
			else:
				__all__ = ["researcharr"]
		except Exception:
			# Fallback: locate the implementation file by scanning plausible
			# locations (cwd, package-relative, and some ancestors). This keeps the
			# compatibility behaviour for older test/CI layouts.
			TOP_LEVEL: Optional[str] = None
			candidates = [
				os.path.join(os.getcwd(), "researcharr.py"),
				os.path.abspath(os.path.join(os.path.dirname(__file__), "researcharr.py")),
				os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "researcharr.py")),
				os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "researcharr.py")),
				os.path.abspath(os.path.join(os.path.dirname(__file__), "researcharr", "researcharr.py")),
			]
			for c in candidates:
				if os.path.isfile(c) and os.path.abspath(c) != os.path.abspath(__file__):
					TOP_LEVEL = c
					break

			if not TOP_LEVEL:
				base = os.path.dirname(__file__)
				for depth in range(1, 6):
					candidate = os.path.abspath(os.path.join(base, *( [".."] * depth), "researcharr.py"))
					if os.path.isfile(candidate) and os.path.abspath(candidate) != os.path.abspath(__file__):
						TOP_LEVEL = candidate
						break

			if TOP_LEVEL:
				spec = importlib.util.spec_from_file_location("researcharr.researcharr", TOP_LEVEL)
				if spec and spec.loader:
					mod = importlib.util.module_from_spec(spec)
					spec.loader.exec_module(mod)  # type: ignore[arg-type]
					# Register the implementation under the canonical name.
					sys.modules["researcharr.researcharr"] = mod
					researcharr = mod
					__all__ = ["researcharr"]
			else:
				researcharr = None

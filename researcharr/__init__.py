"""Compatibility package shim.

This project historically exposes a top-level module layout (e.g. factory.py,
researcharr.py, plugins/*). Tests and some consumers import `researcharr.*`.

To allow `import researcharr.plugins` and `import researcharr.factory` without
restructuring the repository, this package provides lightweight shims that
redirect imports to the existing top-level modules and plugins directory.
"""
# Expose a minimal package namespace; individual submodules are provided as
# small wrapper modules under the same package.
__all__ = []

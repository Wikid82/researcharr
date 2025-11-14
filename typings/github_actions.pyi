"""Type stubs for GitHub Actions secrets/environment variables.

Place simple declarations here so static checkers (pyright/Pylance)
recognize commonly-used environment variables when referenced from
scripts or small helper modules.
"""

# Common workflow-provided token used in Actions runs
GITHUB_TOKEN: str | None
# Token used by Codecov when uploading coverage reports (local or CI overrides)
CODECOV_TOKEN: str | None

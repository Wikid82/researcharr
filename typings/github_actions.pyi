"""Type stubs for GitHub Actions secrets/environment variables.

Place simple declarations here so static checkers (pyright/Pylance)
recognize commonly-used environment variables when referenced from
scripts or small helper modules.
"""

from typing import Optional

# Common workflow-provided token used in Actions runs
GITHUB_TOKEN: Optional[str]
# Token used by Codecov when uploading coverage reports (local or CI overrides)
CODECOV_TOKEN: Optional[str]

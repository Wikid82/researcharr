# Wheelhouse (built wheels) workflow

This project now produces a `wheelhouse/` artifact in CI containing pre-built
wheels for supported Python versions. The multi-version test runner will detect
`wheelhouse/` next to the repository root and install packages from it before
running tests. This reduces variability caused by rebuilding native extensions
in CI and speeds up matrix runs.

How it works

- CI job `build-wheels` runs `cibuildwheel` and uploads the `wheelhouse/`
  directory as an artifact.
- The `test-matrix` job downloads that artifact into the workspace at
  `./wheelhouse` and then invokes `./scripts/ci-multi-version.sh` which will
  install from `/app/wheelhouse` inside the test containers.

Local development

You can build a local wheelhouse for development using the helper script:

```bash
./scripts/build-wheelhouse.sh
# or for full manylinux builds (requires Docker):
./scripts/build-wheelhouse.sh --cibuildwheel
```

Then run the tests using the same script the CI uses (it will pick up the
local `wheelhouse/`):

```bash
./scripts/ci-multi-version.sh --skip-build --versions "3.10 3.11" --log-level summary
```

Notes

- The CI `build-wheels` job is a POC. You may want to adjust the list of
  supported Python versions, cibuildwheel options, or publish the wheels to
  GitHub Packages for long-term storage.

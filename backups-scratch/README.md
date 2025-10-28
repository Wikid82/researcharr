This folder is a local scratch area used when editing or testing backup-related
helpers. It was created during development and intentionally kept out of Git to
avoid confusion with the primary `researcharr` package.

Files
- `researcharr.py` — a small, local shim copied here for reference.

Notes
- This directory is listed in `.gitignore` and will not be committed by default.
- If you want this code tracked, move it into a non-ignored path and add a
  proper module name. Otherwise you can delete this folder once you're done
  with the local edits.

Why this exists
- Keeps temporary or experimental code separate from the canonical package so
  test imports and file names don't collide.

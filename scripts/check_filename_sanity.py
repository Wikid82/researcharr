#!/usr/bin/env python3
import os
import sys
import unicodedata

# Policy values (conservative; adjust as needed)
MAX_COMPONENT_LEN = 120
# Reject control characters, newlines, and likely-accidental quoting in names
FORBIDDEN_CHARS = {"\n", "\r", "\t", "\x00"}

# Heuristic: filenames that start or end with quotes are suspicious
SUSPICIOUS_EDGES = ('"', "'", "`")

# Heuristic: discourage excessive backslashes and raw escaped sequences in a single component
# (legitimate on POSIX, but we only flag egregious cases typical of accidental dumps)
EXCESSIVE_BACKSLASH_THRESHOLD = 8


def is_weird_component(comp: str) -> str | None:
    # Control chars / newlines
    for ch in comp:
        if ch in FORBIDDEN_CHARS or unicodedata.category(ch)[0] == "C":
            return f"contains control/newline char U+{ord(ch):04X}"

    # Leading/trailing quotes
    if comp.startswith(SUSPICIOUS_EDGES) or comp.endswith(SUSPICIOUS_EDGES):
        return "starts/ends with quote character"

    # Excessive backslashes
    if comp.count("\\") >= EXCESSIVE_BACKSLASH_THRESHOLD:
        return "contains excessive backslashes"

    # Overlong component
    if len(comp) > MAX_COMPONENT_LEN:
        return f"component too long ({len(comp)} > {MAX_COMPONENT_LEN})"

    return None


def main(argv: list[str]) -> int:
    if len(argv) <= 1:
        # pre-commit may run without filenames; do nothing
        return 0

    errors: list[str] = []
    for path in argv[1:]:
        # Only check repo-tracked paths
        if not os.path.exists(path):
            # If not present (e.g., deleted), skip
            continue

        # Normalize and split into components
        try:
            norm = os.path.normpath(path)
        except Exception:
            norm = path
        comps = [c for c in norm.split(os.sep) if c not in ("", ".")]

        for comp in comps:
            if reason := is_weird_component(comp):
                errors.append(f"{path}: {reason}")
                break  # report once per path to avoid noise

    if errors:
        print("Filename sanity check failed:\n" + "\n".join(f"  - {e}" for e in errors))
        print(
            "\nTip: rename files to avoid control characters, quotes at edges, and very long path components."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

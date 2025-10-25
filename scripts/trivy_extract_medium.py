#!/usr/bin/env python3
"""Extract MEDIUM vulnerabilities from a Trivy JSON report.

Usage:
  python scripts/trivy_extract_medium.py build/artifacts/trivy-report.json > trivy-medium-summary.txt

This prints a concise table with VulnerabilityID, Package, InstalledVersion, FixedVersion, and Title.
"""
import json
import sys
from pathlib import Path


def extract(path: Path):
    j = json.loads(path.read_text())
    rows = []
    for result in j.get("Results", []):
        target = result.get("Target")
        vulns = result.get("Vulnerabilities") or []
        for v in vulns:
            if v.get("Severity") == "MEDIUM":
                rows.append(
                    (
                        v.get("VulnerabilityID"),
                        v.get("PkgName"),
                        v.get("InstalledVersion"),
                        v.get("FixedVersion") or "(none)",
                        v.get("Title"),
                        target,
                    )
                )
    return rows


def main():
    if len(sys.argv) < 2:
        print("Usage: trivy_extract_medium.py <trivy-json>", file=sys.stderr)
        sys.exit(2)
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"File not found: {p}", file=sys.stderr)
        sys.exit(2)
    rows = extract(p)
    if not rows:
        print("No MEDIUM vulnerabilities found.")
        return
    print("VulnerabilityID\tPackage\tInstalled\tFixed\tTitle\tTarget")
    for r in rows:
        print("\t".join(map(str, r)))


if __name__ == "__main__":
    main()

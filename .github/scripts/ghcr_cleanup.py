#!/usr/bin/env python3
"""
GHCR cleanup utility with safe dry-run and JSON reporting.

Usage examples:
  # dry-run via env (default behavior if not explicitly disabled)
  DRY_RUN=true DAYS=90 GHCR_PAT=... OWNER=... REPO=... python ghcr_cleanup.py

  # CLI flags
  python ghcr_cleanup.py --days 30 --dry-run --json-report report.json

The script will, by default, run in dry-run mode unless explicitly disabled via
`--no-dry-run` or environment variable `DRY_RUN=false`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

GITHUB_API = "https://api.github.com"
DEFAULT_TIMEOUT = 30


def api_path(*parts: str) -> str:
    """Build a GitHub API path from parts, joining with '/'.

    Keeps long f-strings off a single line so linters are happy.
    """
    return "/".join([GITHUB_API.rstrip("/")] + list(parts))


def get_auth_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def list_packages(owner: str, token: str) -> List[Dict[str, Any]]:
    # try org endpoint first, then users
    headers = get_auth_headers(token)
    packages: List[Dict[str, Any]] = []
    for base in (
        api_path("orgs", owner) + "/packages?package_type=container",
        api_path("users", owner) + "/packages?package_type=container",
    ):
        page = 1
        while True:
            # safety cap to avoid infinite loops in case of bad responses
            if page > 10:
                break
            params = {"page": page, "per_page": 100}
            # Some tests stub requests.get and expect the full URL string
            # including query params, so build the URL explicitly.
            q = urlencode(params)
            url = base + ("&" if "?" in base else "?") + q
            r = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
            if r.status_code == 404:
                break
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            packages.extend(data)
            page += 1
        if packages:
            break
    return packages


def list_package_versions(owner: str, package_name: str, token: str) -> List[Dict[str, Any]]:
    headers = get_auth_headers(token)
    versions: List[Dict[str, Any]] = []
    # try org path then user path
    for base in (
        api_path(
            "orgs",
            owner,
            "packages",
            "container",
            package_name,
            "versions",
        ),
        api_path(
            "users",
            owner,
            "packages",
            "container",
            package_name,
            "versions",
        ),
    ):
        page = 1
        while True:
            # safety cap to avoid infinite loops in case of bad responses
            if page > 10:
                break
            params = {"page": page, "per_page": 100}
            # Build URL with page params so tests that inspect the URL work
            q = urlencode(params)
            url = base + ("&" if "?" in base else "?") + q
            r = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
            if r.status_code == 404:
                break
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            versions.extend(data)
            page += 1
        if versions:
            break
    # deduplicate by id (some test stubs return the same page multiple times)
    seen_ids = set()
    unique_versions: List[Dict[str, Any]] = []
    for v in versions:
        vid = v.get("id")
        if vid not in seen_ids:
            seen_ids.add(vid)
            unique_versions.append(v)
    return unique_versions


def delete_version(
    owner: str,
    package_name: str,
    version_id: int,
    token: str,
) -> bool:
    # try org path then user path
    headers = get_auth_headers(token)
    for base in (
        api_path(
            "orgs",
            owner,
            "packages",
            "container",
            package_name,
            str(version_id),
        ),
        api_path(
            "users",
            owner,
            "packages",
            "container",
            package_name,
            str(version_id),
        ),
    ):
        r = requests.delete(base, headers=headers, timeout=DEFAULT_TIMEOUT)
        if r.status_code in (204, 202):
            return True
        # if 404 try the next base
        if r.status_code == 404:
            continue
        # otherwise, print and return False
        # Use multiple print args to avoid a very long single string line
        print(
            "Failed to delete version",
            version_id,
            r.status_code,
            r.text,
        )
        return False
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GHCR cleanup with dry-run and JSON reporting")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Perform a dry run; do not delete any versions",
    )
    group.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="Perform deletions (disable dry run)",
    )
    parser.set_defaults(dry_run=None)
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Retention in days (default from DAYS env or 90)",
    )
    parser.add_argument(
        "--json-report",
        type=str,
        default=None,
        help=("Path to write JSON report"),
    )
    parser.add_argument(
        "--protected-tags",
        type=str,
        default="main,development,latest",
        help="Comma-separated protected tags",
    )
    return parser.parse_args()


def truthy_env(val: Optional[str]) -> Optional[bool]:
    if val is None:
        return None
    v = val.lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return None


def main() -> None:
    args = parse_args()

    env_dry = truthy_env(os.getenv("DRY_RUN"))
    if args.dry_run is None:
        if env_dry is None:
            dry_run = True  # safe default
        else:
            dry_run = env_dry
    else:
        dry_run = args.dry_run

    token = os.getenv("GHCR_TOKEN") or os.getenv("GHCR_PAT")
    if not token:
        print("GHCR_PAT/GHCR_TOKEN not set in environment. Exiting.")
        sys.exit(1)

    owner = os.getenv("OWNER")
    repo = os.getenv("REPO")
    days = args.days if args.days is not None else int(os.getenv("DAYS", "90"))
    protected_tags = set(t.strip() for t in (args.protected_tags or "").split(",") if t.strip())

    if not owner or not repo:
        gh_repo = os.getenv("GITHUB_REPOSITORY")
        if gh_repo and "/" in gh_repo:
            owner, repo = gh_repo.split("/", 1)

    if not owner or not repo:
        print("OWNER and REPO must be provided. Exiting.")
        sys.exit(1)

    keep_since = datetime.now(timezone.utc) - timedelta(days=days)
    print(
        "Owner: %s, Package: %s, keep versions newer than: %s"
        % (owner, repo, keep_since.isoformat())
    )

    packages = list_packages(owner, token)
    target = None
    for p in packages:
        if p.get("name") == repo:
            target = p
            break

    if not target:
        print("No container package named '%s' found in account '%s'. Exiting." % (repo, owner))
        sys.exit(0)

    print(f"Found package: {target.get('name')} (id: {target.get('id')})")

    versions = list_package_versions(owner, repo, token)
    print(f"Found {len(versions)} versions for package {repo}")

    report: Dict[str, Any] = {
        "owner": owner,
        "package": repo,
        "scanned": len(versions),
        "days": days,
        "keep_since": keep_since.isoformat(),
        "protected_tags": sorted(list(protected_tags)),
        "candidates": [],
    }

    for v in versions:
        version_id = v.get("id")
        created_at = v.get("created_at")
        metadata = v.get("metadata", {}) or {}
        tags = []
        try:
            tags = metadata.get("container", {}).get("tags", []) or []
        except Exception:
            tags = []

        tag_set = set(tags)
        decision = "KEEP"
        reason = None

        if tag_set & protected_tags:
            decision = "SKIP_PROTECTED"
            matched = sorted(list(tag_set & protected_tags))
            reason = "protected tags: %s" % (matched,)
        else:
            if created_at is None:
                decision = "SKIP_BAD_DATE"
                reason = "created_at is None"
            else:
                try:
                    created_at_fixed = created_at.replace("Z", "+00:00")
                    created_dt = datetime.fromisoformat(created_at_fixed)
                except Exception:
                    decision = "SKIP_BAD_DATE"
                    reason = f"could not parse created_at: {created_at}"
                else:
                    if created_dt < keep_since:
                        decision = "DELETE"
                        reason = "older than retention"
                    else:
                        decision = "KEEP"
                        reason = "newer than retention"

        report["candidates"].append(
            {
                "version_id": version_id,
                "created_at": created_at,
                "tags": tags,
                "decision": decision,
                "reason": reason,
            }
        )

    would_delete = []
    for c in report["candidates"]:
        if c.get("decision") == "DELETE":
            would_delete.append(c)
    report["would_delete_count"] = len(would_delete)

    # write report if requested
    env_report = os.getenv("JSON_REPORT")
    if args.json_report:
        json_path = args.json_report
    elif env_report:
        json_path = env_report
    else:
        json_path = "ghcr_cleanup_report.json"
    try:
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"Wrote JSON report to {json_path}")
    except Exception as exc:
        print(f"Failed to write JSON report to {json_path}: {exc}")

    if dry_run:
        print("Dry run: %s versions WOULD be deleted." % (len(would_delete),))
        for c in would_delete:
            print(
                "[DRY] would delete version %s created_at=%s tags=%s"
                % (c["version_id"], c["created_at"], c["tags"])
            )
        return

    # perform deletions
    deleted = []
    failed = []
    for c in would_delete:
        vid = c["version_id"]
        print(
            "Deleting version %s created_at=%s tags=%s..." % (vid, c["created_at"], c["tags"]),
            end=" ",
        )
        ok = delete_version(owner, repo, vid, token)
        if ok:
            print("OK")
            deleted.append(vid)
        else:
            print("FAILED")
            failed.append(vid)

    report["deleted"] = deleted
    report["failed"] = failed
    # rewrite report with final deletion results
    try:
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"Wrote JSON report with deletion results to {json_path}")
    except Exception as exc:
        print(f"Failed to write JSON report: {exc}")


if __name__ == "__main__":
    main()

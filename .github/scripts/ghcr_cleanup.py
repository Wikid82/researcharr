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

import requests

GITHUB_API = "https://api.github.com"


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
        f"{GITHUB_API}/orgs/{owner}/packages?package_type=container",
        f"{GITHUB_API}/users/{owner}/packages?package_type=container",
    ):
        page = 1
        while True:
            r = requests.get(base + f"&page={page}&per_page=100", headers=headers)
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


def list_package_versions(
    owner: str, package_name: str, token: str
) -> List[Dict[str, Any]]:
    headers = get_auth_headers(token)
    versions: List[Dict[str, Any]] = []
    # try org path then user path
    for base in (
        f"{GITHUB_API}/orgs/{owner}/packages/container/{package_name}/versions",
        f"{GITHUB_API}/users/{owner}/packages/container/{package_name}/versions",
    ):
        page = 1
        while True:
            r = requests.get(base + f"?page={page}&per_page=100", headers=headers)
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
    return versions


def delete_version(owner: str, package_name: str, version_id: int, token: str) -> bool:
    # try org path then user path
    headers = get_auth_headers(token)
    for base in (
        f"{GITHUB_API}/orgs/{owner}/packages/container/{package_name}/versions/{version_id}",
        f"{GITHUB_API}/users/{owner}/packages/container/{package_name}/versions/{version_id}",
    ):
        r = requests.delete(base, headers=headers)
        if r.status_code in (204, 202):
            return True
        # if 404 try the next base
        if r.status_code == 404:
            continue
        # otherwise, print and return False
        print(f"Failed to delete version {version_id}: {r.status_code} {r.text}")
        return False
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GHCR cleanup with dry-run and JSON reporting"
    )
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
        "--json-report", type=str, default=None, help="Path to write JSON report"
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
    protected_tags = set(
        t.strip() for t in (args.protected_tags or "").split(",") if t.strip()
    )

    if not owner or not repo:
        gh_repo = os.getenv("GITHUB_REPOSITORY")
        if gh_repo and "/" in gh_repo:
            owner, repo = gh_repo.split("/", 1)

    if not owner or not repo:
        print("OWNER and REPO must be provided. Exiting.")
        sys.exit(1)

    keep_since = datetime.now(timezone.utc) - timedelta(days=days)
    print(
        f"Owner: {owner}, Package: {repo}, keep versions newer than: {keep_since.isoformat()}"
    )

    packages = list_packages(owner, token)
    target = None
    for p in packages:
        if p.get("name") == repo:
            target = p
            break

    if not target:
        print(
            f"No container package named '{repo}' found in account '{owner}'. Exiting."
        )
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
            reason = f"protected tags: {sorted(list(tag_set & protected_tags))}"
        else:
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
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

    would_delete = [c for c in report["candidates"] if c["decision"] == "DELETE"]
    report["would_delete_count"] = len(would_delete)

    # write report if requested
    json_path = (
        args.json_report or os.getenv("JSON_REPORT") or "ghcr_cleanup_report.json"
    )
    try:
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"Wrote JSON report to {json_path}")
    except Exception as exc:
        print(f"Failed to write JSON report to {json_path}: {exc}")

    if dry_run:
        print(
            f"Dry run mode: {len(would_delete)} versions WOULD be deleted. No deletions performed."
        )
        for c in would_delete:
            print(
                f"[DRY] would delete version {c['version_id']} created_at={c['created_at']} tags={c['tags']}"
            )
        return

    # perform deletions
    deleted = []
    failed = []
    for c in would_delete:
        vid = c["version_id"]
        print(
            f"Deleting version {vid} created_at={c['created_at']} tags={c['tags']}...",
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

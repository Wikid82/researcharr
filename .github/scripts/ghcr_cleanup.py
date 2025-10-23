#!/usr/bin/env python3
"""
Delete GHCR (GitHub Container Registry) package versions older than a threshold.

Environment variables:
  GHCR_TOKEN - personal access token with 'delete:packages' (and read scope) for owner
  OWNER      - repository owner/org (defaults to repo owner)
  REPO       - repository name
  DAYS       - number of days to keep (default 90)

This script will:
 - find the container package matching the repository name under the owner account
 - list package versions
 - delete versions older than DAYS which do not have tags: 'main', 'development', or 'latest'

NOTE: This action operates at the account package level. Be careful and test with small values first.
"""
import os
import sys
import time
import requests
from datetime import datetime, timezone, timedelta


GITHUB_API = "https://api.github.com"


def get_auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def list_packages(owner, token):
    url = f"{GITHUB_API}/users/{owner}/packages?package_type=container"
    headers = get_auth_headers(token)
    packages = []
    page = 1
    while True:
        r = requests.get(url + f"&page={page}&per_page=100", headers=headers)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        packages.extend(data)
        page += 1
    return packages


def list_package_versions(owner, package_name, token):
    url = f"{GITHUB_API}/users/{owner}/packages/container/{package_name}/versions"
    headers = get_auth_headers(token)
    versions = []
    page = 1
    while True:
        r = requests.get(url + f"?page={page}&per_page=100", headers=headers)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        versions.extend(data)
        page += 1
    return versions


def delete_version(owner, package_name, version_id, token):
    url = f"{GITHUB_API}/users/{owner}/packages/container/{package_name}/versions/{version_id}"
    headers = get_auth_headers(token)
    r = requests.delete(url, headers=headers)
    if r.status_code in (204, 202):
        return True
    else:
        print(f"Failed to delete version {version_id}: {r.status_code} {r.text}")
        return False


def main():
    token = os.getenv("GHCR_TOKEN") or os.getenv("GHCR_PAT")
    if not token:
        print("GHCR_PAT/GHCR_TOKEN not set in environment. Exiting.")
        sys.exit(1)

    owner = os.getenv("OWNER")
    repo = os.getenv("REPO")
    days = int(os.getenv("DAYS", "90"))

    if not owner or not repo:
        # try to split GITHUB_REPOSITORY
        gh_repo = os.getenv("GITHUB_REPOSITORY")
        if gh_repo and "/" in gh_repo:
            owner, repo = gh_repo.split("/", 1)

    if not owner or not repo:
        print("OWNER and REPO must be provided. Exiting.")
        sys.exit(1)

    keep_since = datetime.now(timezone.utc) - timedelta(days=days)
    print(f"Owner: {owner}, Package: {repo}, keep versions newer than: {keep_since.isoformat()}")

    packages = list_packages(owner, token)
    # find package with exact repo name
    target = None
    for p in packages:
        if p.get("name") == repo:
            target = p
            break

    if not target:
        print(f"No container package named '{repo}' found in account '{owner}'. Exiting.")
        sys.exit(0)

    print(f"Found package: {target.get('name')} (id: {target.get('id')})")

    versions = list_package_versions(owner, repo, token)
    print(f"Found {len(versions)} versions for package {repo}")

    protected_tags = {"main", "development", "latest"}
    to_delete = []
    for v in versions:
        created_at = v.get("created_at")
        version_id = v.get("id")
        metadata = v.get("metadata", {})
        # metadata may contain container.tags
        tags = []
        try:
            tags = metadata.get("container", {}).get("tags", []) or []
        except Exception:
            tags = []

        tag_set = set(tags)

        if tag_set & protected_tags:
            print(f"Skipping version {version_id} due to protected tag(s): {tag_set & protected_tags}")
            continue

        # parse created_at
        try:
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except Exception:
            print(f"Could not parse created_at for version {version_id}: {created_at}. Skipping.")
            continue

        if created_dt < keep_since:
            to_delete.append((version_id, created_at, tags))

    print(f"Versions to delete: {len(to_delete)}")
    for version_id, created_at, tags in to_delete:
        print(f"Deleting version {version_id} created at {created_at} tags={tags}...", end=" ")
        ok = delete_version(owner, repo, version_id, token)
        print("OK" if ok else "FAILED")


if __name__ == "__main__":
    main()

# PAT Setup Guide for Full Project Automation

## 🔑 Step 1: Create Personal Access Token (PAT)

1. **Go to GitHub Settings**: https://github.com/settings/personal-access-tokens/new

2. **Choose "Fine-grained personal access tokens"**

3. **Configure the token**:
   - **Token name**: `researcharr-project-automation`
   - **Expiration**: Choose your preferred duration (90 days recommended)
   - **Resource owner**: Select your account (Wikid82)
   - **Repository access**: Selected repositories → `researcharr`

4. **Set Repository permissions**:
   - `Issues`: **Write**
   - `Metadata`: **Read**
   - `Pull requests`: **Write**

5. **Set Account permissions**:
   - `Projects`: **Write** ⭐ (This is the critical permission!)

6. **Generate token** and copy it immediately

## 🔐 Step 2: Add PAT as Repository Secret

1. **Go to repository secrets**: https://github.com/Wikid82/researcharr/settings/secrets/actions

2. **Click "New repository secret"**

3. **Configure secret**:
   - **Name**: `GITHUB_TOKEN`
   - **Secret**: [Paste your PAT here]

4. **Click "Add secret"**

## 🚀 Step 3: Test the Automation

Once you've added the `GITHUB_TOKEN` secret:

### Option A: Run the bulk add workflow
```bash
# This will add all issues #80-113 to the project board
gh workflow run add-all-issues-to-project.yml
```

```markdown
# PAT & Token Guide — updated

This repository now prefers the Actions-provided `GITHUB_TOKEN` in workflows. You generally do NOT need to create or upload a Personal Access Token (PAT) as a secret for the built-in automation to work. The guidance below explains when you still might need a PAT (for local runs or exceptional cross-repo needs), recommended secret names, required scopes, and how to test a token locally.

## Preferred approach: `GITHUB_TOKEN`

- All workflows in this repository use `secrets.GITHUB_TOKEN` by default.
- Do not create or overwrite a secret named `GITHUB_TOKEN` in the repository—this value is injected by GitHub Actions automatically. Overwriting it with a personal PAT is not recommended.

## When to create a PAT

- Running automation locally (e.g. `.github/scripts/ghcr_cleanup.py --dry-run`) from your machine.
- Performing cross-repo operations or admin tasks that require scopes not granted to the `GITHUB_TOKEN` in Actions.

## Recommended secret names (if you must add a PAT)

- `GHCR_PAT` or `GHCR_TOKEN`: for scripts that interact with GitHub Packages / GHCR locally or in custom CI.
- `PROJECT_PAT`: only if you have a customized workflow that explicitly expects it (not required by default workflows in this repo).

## Required scopes

- `read:packages` and `delete:packages` — required to list/delete GHCR/container package versions.
- `repo` or more granular repo scopes — only if you need repository content or issue access beyond what `GITHUB_TOKEN` provides.
- `projects` / `projects:write` scope (for older classic Projects APIs) — only if you are using endpoints that require it; the repository workflows are designed to work with `GITHUB_TOKEN` and project permissions when possible.

## How to create a PAT (if needed)

1. Go to https://github.com/settings/tokens/new
2. Name it (e.g. `researcharr-local-cleanup`) and choose an expiration
3. Enable only the minimal scopes required for your use-case
4. Copy the token value

## Add a PAT as a repository secret (only if necessary)

1. In the repository: Settings → Secrets and variables → Actions → New repository secret
2. Use one of the recommended names (`GHCR_PAT`, `GHCR_TOKEN`, etc.)

Note: The repository's workflows do not require `PROJECT_TOKEN` by default; do not add `PROJECT_TOKEN` unless explicitly needed by your environment.

## Testing a token locally

You can test any token locally by exporting it and calling the API. The cleanup script also performs a `GET /user` check and prints diagnostics when tokens fail.

Example quick check using curl:

```bash
export GHCR_PAT="ghp_..."
curl -i -H "Authorization: token $GHCR_PAT" https://api.github.com/user
```

- A successful response returns your authenticated user and a `200` status.
- A `401` with `Bad credentials` indicates the token is invalid or missing scopes.

## Example: run the cleanup script locally (dry-run)

```bash
# set a PAT in GHCR_PAT (only for local runs)
export GHCR_PAT="ghp_..."
python .github/scripts/ghcr_cleanup.py --dry-run
```

The script will print the request URL, response status, response headers, and response body for failed requests to make debugging easier.

## Workflow permissions (what to set in workflows)

If you encounter permission errors from Actions, update the `permissions` block in the workflow YAML to include the capabilities required by that job. Example:

```yaml
permissions:
  packages: write    # required for deleting GHCR/container packages
  contents: read     # required for repository contents access
  issues: write      # if workflows create/update issues or project items
```

Grant the minimal permissions needed for each workflow.

## Troubleshooting

- If automation fails in Actions, inspect the workflow logs (`Actions` tab) and check the `x-oauth-scopes` and `x-ratelimit-*` headers printed by the cleanup script when applicable.
- For local testing, ensure your PAT has the `read:packages` / `delete:packages` scopes when interacting with GHCR.

## Quick checklist

- Use `secrets.GITHUB_TOKEN` in Actions — do not override it.
- For local runs, export `GHCR_PAT` and test with `curl` before running scripts.
- Adjust workflow `permissions` if you see permission-related failures.

```

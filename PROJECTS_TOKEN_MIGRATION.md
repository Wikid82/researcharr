# Projects Token Migration Summary

## Updated Files

All project-related GitHub Actions workflows have been updated to use `PROJECTS_TOKEN` instead of inconsistent token references:

### ✅ Updated Workflows:

1. **`.github/workflows/project-automation.yml`**
   - Global env: `GITHUB_TOKEN: ${{ secrets.PROJECTS_TOKEN || secrets.GITHUB_TOKEN }}`
   - Add issue to project step: Updated
   - Update issue status step: Updated

2. **`.github/workflows/sync-issues-to-project.yml`**
   - Global env: `GITHUB_TOKEN: ${{ secrets.PROJECTS_TOKEN || secrets.GITHUB_TOKEN }}`
   - Sync to project step: Already correct

3. **`.github/workflows/add-all-issues-to-project.yml`**
   - Add all issues step: `GITHUB_TOKEN: ${{ secrets.PROJECTS_TOKEN || secrets.GITHUB_TOKEN }}`

4. **`.github/workflows/create-project.yml`**
   - Create Project step: `GITHUB_TOKEN: ${{ secrets.PROJECTS_TOKEN || secrets.GITHUB_TOKEN }}`

5. **`.github/workflows/sync-project.yml`**
   - Get project data step: Updated
   - Get all issues step: Updated
   - Get all pull requests step: Updated
   - Add issues to project step: Updated
   - Add pull requests to project step: Updated

6. **`.github/workflows/migrate-issues-to-project.yml`**
   - Already using `PROJECTS_TOKEN` ✅

7. **`scripts/migrate-all-issues.py`**
   - Updated to check `PROJECTS_TOKEN` first, then fall back to `GITHUB_TOKEN`
   - Removed hardcoded token and debug output

### 🔧 Token Priority Order:
All workflows now use this fallback pattern:
```yaml
GITHUB_TOKEN: ${{ secrets.PROJECTS_TOKEN || secrets.GITHUB_TOKEN }}
```

This means:
1. **First priority**: `PROJECTS_TOKEN` (your classic token with project permissions)
2. **Fallback**: `GITHUB_TOKEN` (default repo token)

## Next Steps:

1. **Set the repository secret**:
   - Go to repo **Settings** → **Secrets and variables** → **Actions**
   - Add or update `PROJECTS_TOKEN` with your classic token: `github_pat_11BKCW5NI0[REDACTED]`

2. **Test the migration**:
   ```bash
   export PROJECTS_TOKEN=github_pat_11BKCW5NI0[REDACTED]
   python scripts/migrate-all-issues.py
   ```

3. **Test real-time automation**: Create a new test issue to verify the project automation workflow works

## Notes:
- All workflows maintain backward compatibility by falling back to `GITHUB_TOKEN`
- The classic token should have `repo` and `project` scopes for full functionality
- Migration workflow already had the correct token reference

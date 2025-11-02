# Renovate Bot Configuration Guide

This document explains the Renovate bot configuration used in this project and the rationale behind each setting.

## Overview

Renovate is an automated dependency update tool that creates pull requests to keep dependencies up-to-date. Our configuration is designed to balance automation with safety and maintainability.

## Configuration File

The Renovate configuration is located in `renovate.json` at the root of the repository.

## Key Features

### 1. Recommended Presets

```json
"extends": [
  "config:recommended",
  ":dependencyDashboard",
  ":semanticCommits",
  ":enablePreCommit",
  "group:monorepos",
  "group:recommended",
  "workarounds:all"
]
```

**Presets Explained:**

- **`config:recommended`**: Base Renovate recommended configuration
- **`:dependencyDashboard`**: Creates a GitHub issue that lists all pending updates
- **`:semanticCommits`**: Uses semantic commit messages (e.g., `chore(deps):`)
- **`:enablePreCommit`**: Updates pre-commit hooks automatically
- **`group:monorepos`**: Groups dependencies from monorepos together
- **`group:recommended`**: Groups related dependencies (e.g., linters, testing tools)
- **`workarounds:all`**: Applies known workarounds for common Renovate issues

### 2. Schedule Configuration

```json
"schedule": ["before 6am on Monday"],
"timezone": "UTC",
"prConcurrentLimit": 5,
"prHourlyLimit": 2
```

**Why This Matters:**
- Updates run weekly on Monday mornings to give the team time to review
- Limits concurrent PRs to avoid overwhelming reviewers
- Prevents rate-limiting issues with external services

### 3. Stability Days

```json
"stabilityDays": 3
```

**Purpose:**
- Waits 3 days after a new version is published before creating a PR
- Allows time for community to discover critical bugs
- Reduces risk of adopting broken releases

### 4. Vulnerability Alerts

```json
"vulnerabilityAlerts": {
  "enabled": true,
  "labels": ["security"],
  "stabilityDays": 0
}
```

**Security First:**
- Security updates bypass the stability period
- Automatically labeled for easy identification
- Can be processed immediately to protect the project

### 5. Automerge Strategy

```json
{
  "description": "Automerge non-major updates",
  "matchUpdateTypes": ["minor", "patch", "pin", "digest"],
  "automerge": true,
  "automergeType": "pr",
  "automergeStrategy": "squash"
}
```

**Automation with Safety:**
- Only automerges minor and patch updates
- Major updates require manual review
- Uses squash strategy for clean commit history
- Requires CI checks to pass before merging

### 6. Dependency Grouping

The configuration groups related dependencies:

**Python Dependencies:**
```json
{
  "matchDatasources": ["pypi"],
  "groupName": "Python dependencies"
}
```
- All Python package updates in one PR
- Easier to test compatibility between packages

**Docker Base Images:**
```json
{
  "matchDatasources": ["docker"],
  "matchPackagePatterns": ["^python$"],
  "groupName": "Docker Python base images",
  "schedule": ["before 6am on the first day of the month"]
}
```
- Base image updates are less frequent (monthly)
- Requires more thorough testing

**GitHub Actions:**
```json
{
  "matchManagers": ["github-actions"],
  "groupName": "GitHub Actions",
  "automerge": true,
  "pinDigests": true
}
```
- Updates workflow actions together
- Pins to specific SHA digests for security
- Can be automerged as they rarely break

### 7. Major Update Handling

```json
{
  "matchUpdateTypes": ["major"],
  "automerge": false,
  "labels": ["dependencies", "major-update"],
  "stabilityDays": 7
}
```

**Extra Caution:**
- Never automerges major updates
- Extra stability period (7 days)
- Special labels for visibility

### 8. Development Dependencies

```json
{
  "matchFileNames": ["requirements-dev.txt"],
  "rangeStrategy": "pin"
}
```

**Predictable Development:**
- Pins exact versions for development tools
- Ensures consistent developer environments
- Reduces "works on my machine" issues

### 9. Frozen Requirements

```json
{
  "matchFileNames": ["requirements-frozen.txt"],
  "enabled": false
}
```

**Manual Control:**
- Disables automatic updates for frozen dependencies
- Allows manual version management when needed
- Useful for locked production environments

## Workarounds Included

The `workarounds:all` preset includes fixes for known issues:

1. **Docker versioning**: Handles Docker tags correctly
2. **Python constraints**: Properly parses Python version specifiers
3. **Poetry/pip compatibility**: Manages different package manager quirks
4. **Rate limiting**: Implements backoff strategies
5. **Git authentication**: Handles private registries properly

## Customization

### Adding Ignored Dependencies

To ignore specific dependencies:

```json
"ignoreDeps": ["package-name"]
```

### Adjusting Schedule

Change the schedule to fit your workflow:

```json
"schedule": ["after 10pm every weekday", "before 5am every weekday"]
```

### Modifying Automerge Rules

To disable automerge entirely:

```json
"automerge": false
```

Or create more specific rules in `packageRules`.

## Best Practices

1. **Review the Dependency Dashboard**: Check the Renovate dashboard issue regularly
2. **Monitor Automerged PRs**: Even automated merges should be spot-checked
3. **Test Major Updates**: Always test major version updates thoroughly
4. **Security First**: Prioritize security updates
5. **Keep CI Green**: Ensure tests pass before and after updates

## Troubleshooting

### Too Many PRs

Increase `stabilityDays` or adjust `prConcurrentLimit`.

### Updates Not Appearing

Check:
- Is the schedule configured correctly?
- Are dependencies in `ignoreDeps`?
- Does the branch target (`baseBranches`) exist?

### Automerge Not Working

Ensure:
- Branch protection rules allow automerge
- CI checks are configured and passing
- The update type matches automerge rules

## References

- [Renovate Documentation](https://docs.renovatebot.com/)
- [Configuration Options](https://docs.renovatebot.com/configuration-options/)
- [Preset Configs](https://docs.renovatebot.com/presets-config/)
- [Python Manager](https://docs.renovatebot.com/modules/manager/pip_requirements/)

## Maintenance

This configuration should be reviewed periodically:

- **Quarterly**: Review automerge settings based on incident rate
- **Bi-annually**: Evaluate new Renovate presets
- **After incidents**: Adjust rules if automated updates cause issues

Last updated: 2025-11-02

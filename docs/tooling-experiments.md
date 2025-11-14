# Experimental Tooling: Sourcery & Vulture

Sourcery now runs automatically as part of `pre-commit` (limited to the highest-signal rules listed below) while Vulture remains opt-in. Use this doc when you need the full ad-hoc scans, want to tweak the rule tiers, or simply forget the setup steps.

## Sourcery in pre-commit (high/medium rule tiers)

The `sourcery` hook in `.pre-commit-config.yaml` executes `sourcery review --check researcharr` with a hand-curated rule allowlist. Those rules are grouped into the same "high" and "medium" buckets that power `reports/sourcery-priority.json`:

**High priority (correctness & safety)**
- `raise-specific-error`
- `raise-from-previous-error`
- `remove-redundant-exception`
- `simplify-single-exception-tuple`
- `remove-none-from-default-get`
- `remove-redundant-path-exists`

**Medium priority (readability & maintainability)**
- `collection-into-set`
- `dict-assign-update-to-union`
- `hoist-statement-from-if`
- `introduce-default-else`
- `merge-list-appends-into-extend`
- `merge-nested-ifs`
- `remove-unnecessary-else`
- `swap-if-else-branches`

If you want to tighten or relax what runs before each commit, edit the `--enable <rule-id>` entries in the hook and update this section (and the JSON report, if you keep it synchronized). The hook installs Sourcery automatically, but you still need to provide credentials once per machine—either run `sourcery login` or export `SOURCERY_TOKEN` so that both `pre-commit` and the manual tasks can authenticate.

## 1. One-time setup

```bash
source .venv/bin/activate
python -m pip install --upgrade "sourcery-cli>=1.16" vulture
```

These commands are still useful when you want to run the full Sourcery/Vulture scans manually (outside of the limited pre-commit tier). Sourcery also needs an API token:

1. Create/sign in to a Sourcery account.
2. Run `sourcery login` once or export an existing token:
   ```bash
   export SOURCERY_TOKEN="<paste token>"
   ```
   The VS Code task automatically forwards `SOURCERY_TOKEN` if it is set in your shell/OS.

Troubleshooting:

- If the task output says `sourcery: command not found` or `vulture: command not found`, re-run the commands above to make sure both CLIs are installed inside `.venv`, then verify with:
   ```bash
   source .venv/bin/activate
   which sourcery
   which vulture
   ```
   Both should resolve to paths under `.venv/bin`.
- Sourcery needs to be authenticated once per machine (`sourcery login`). If it prompts for a token mid-run, finish the login flow and re-run the task.
- Vulture exits with code `3` when it finds issues. That’s expected—inspect the report and decide whether to act on the findings; the non-zero exit code only matters if you script against it.

## 2. Running the trial tasks

Open the command palette → `Tasks: Run Task` and pick:

### `Sourcery: Analyze (Trial)`
- Prompts for a path (default `researcharr`).
- Executes `sourcery review <path>` inside the virtualenv.
- Output shows suggested refactors/diffs; none are applied automatically.

### `Vulture: Dead Code Scan (Trial)`
- Scans `researcharr/` and `scripts/` by default.
- Prompts for extra CLI arguments (default `--min-confidence 80`).
- Use flags like `--exclude` or `--sort-by-size` to refine results.

## 3. Reviewing results

- Treat both reports as advisory. Anything actionable can be turned into a normal issue/PR.
- Because these runs are local-only, you can tweak thresholds or scopes without affecting other developers.
- Sourcery already blocks on the curated rule set via pre-commit, but these wider runs tell you whether we should promote additional rules (or drop noisy ones) in the future.

## 4. Cleanup (optional)

To remove the tools after experimenting:

```bash
source .venv/bin/activate
python -m pip uninstall sourcery-cli vulture
```

No repository files or workflows depend on them, so uninstalling is safe.

## 5. Capturing priority-rule JSON

To review only the high-value Sourcery rules discussed earlier:

```bash
cd /home/jeremy/Server/Projects/researcharr
source .venv/bin/activate
sourcery review researcharr --csv --no-summary > sourcery-report.csv
python scripts/filter_sourcery_priority.py  # or run the inline snippet below
```

Inline snippet (used most recently) that writes `reports/sourcery-priority.json`:

```bash
python - <<'PY'
import csv, json
from pathlib import Path

priority_rules = {
   "raise-specific-error",
   "raise-from-previous-error",
   "remove-redundant-exception",
   "simplify-single-exception-tuple",
   "remove-redundant-path-exists",
   "remove-none-from-default-get",
   "remove-unnecessary-else",
   "swap-if-else-branches",
   "merge-nested-ifs",
   "hoist-statement-from-if",
   "collection-into-set",
   "dict-assign-update-to-union",
   "merge-list-appends-into-extend",
   "introduce-default-else",
}

rows = []
with open("sourcery-report.csv", newline="", encoding="utf-8") as fh:
   for row in csv.DictReader(fh):
      if row["rule"] in priority_rules:
         rows.append(row)

Path("reports").mkdir(exist_ok=True)
with open("reports/sourcery-priority.json", "w", encoding="utf-8") as fh:
   json.dump({"priority_rules": sorted(priority_rules), "findings": rows, "total_findings": len(rows)}, fh, indent=2)
PY
```

The generated JSON currently lists 24 findings under `reports/sourcery-priority.json`. Re-run the steps above after new Sourcery scans (or after changing the pre-commit allowlist) to refresh the file.

Development helper

Use the provided helper to run the development compose stack with file-watching enabled. This will rebuild/recreate containers when source files change.

Quick start:

```bash
# from repository root
./scripts/dev-up.sh
```

Notes:
- The script runs `docker compose -f docker-compose.feat.yml up --build --watch`.
- If you prefer detaching, add `-d` to the command or run the `docker compose` command directly.
- You can change the compose file by setting the COMPOSE_FILE variable at the top of `scripts/dev-up.sh`.

Propagating upstream changes to downstream branches
--------------------------------------------------

When automated tools (for example Renovate) open or merge PRs to `main`, you may want those changes tested against downstream branches (for example `development`). A workflow has been added to create PRs from `main` into downstream branches automatically: `.github/workflows/propagate-main-to-downstream.yml`.

If you need to backfill older changes (created before automation), use the GitHub CLI to create PRs from `main` into the downstream branch, e.g.:

```bash
# create a PR from `main` into `development`
gh pr create --title "chore(ci): propagate main -> development" --body "Backfill PR to test compatibility" --base development --head main
```

If you prefer a scripted approach to create PRs for multiple downstream branches, run:

```bash
for base in development staging; do
	gh pr create --title "chore(ci): propagate main -> $base" \
		--body "Automated backfill created by maintainer" --base $base --head main || true
done
```

Note: If a merge between `main` and a downstream branch results in conflicts, the created PR will report merge conflicts and must be resolved manually. For complex backfills you can create a temporary branch, attempt a merge locally, resolve conflicts, push the branch, and open a PR for review.

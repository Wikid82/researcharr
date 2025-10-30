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

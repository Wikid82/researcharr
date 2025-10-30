SHELL := /bin/bash
.PHONY: dev dev-detach build test stop logs

dev:
	# Start development stack in foreground with file-watch enabled
	./scripts/dev-up.sh

dev-detach:
	# Start development stack detached (useful for CI or background runs)
	./scripts/dev-up.sh -d

build:
	# Build the local debug image
	docker compose -f docker-compose.feat.yml build

test:
	# Run the local pytest suite
	python -m pytest -q

stop:
	# Stop and remove the development stack
	docker compose -f docker-compose.feat.yml down

logs:
	# Follow logs for the compose project
	docker compose -f docker-compose.feat.yml logs -f
.PHONY: docs-preview

# Serve the docs/ folder locally at http://localhost:8000
docs-preview:
	python3 -m http.server --directory docs 8000

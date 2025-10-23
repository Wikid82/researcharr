# Getting Started

Follow these steps to run researcharr locally or in Docker.

Local (development)

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app (example):

```bash
python researcharr.py serve
```

Docker

1. Build and run using Docker Compose (example):

```bash
docker-compose up -d --build
```

2. The web UI is available on port `2929` by default.

Configuration and config files

- See `config.example.yml` for configuration options. The container will auto-create `/config/config.yml` from the example if it's missing.

Health & Metrics

- The app exposes `/health` and `/metrics` for monitoring and Docker healthchecks.

Support

- See the wiki `FAQ.md` and `Roadmap.md` for additional project information.

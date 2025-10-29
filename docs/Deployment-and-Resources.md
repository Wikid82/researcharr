# Deployment and Resource Recommendations

This page gives practical examples for running researcharr with resource
limits and job runtime safeguards. It shows Docker, Docker Compose, and
Kubernetes examples and explains the environment variables used by the
application to bound scheduled job runs.

Environment variables (runtime safety)

- JOB_TIMEOUT: integer seconds. If set and > 0, scheduled jobs launched by
  the in-process scheduler will be killed after this many seconds. Default: 0
  (no timeout).
- JOB_RLIMIT_AS_MB: integer megabytes. If set, the child process will have
  its virtual memory (address space) limited to this many MB. This uses
  Unix RLIMIT_AS and is only applied on platforms that support the
  `resource` module.
- JOB_RLIMIT_CPU_SECONDS: integer seconds. If set, the child process will
  be limited to this many CPU seconds (RLIMIT_CPU).
- RUN_JOB_CONCURRENCY: integer. When set to `1` (the default), the
  scheduler will skip launching a new run if a previous run is still
  executing. Values >1 allow that many concurrent jobs.

Docker (recommended quick run)

Example run with a 300s job timeout and modest container limits:

```bash
docker run -d \
  --name=researcharr \
  -v /path/to/config:/config \
  -p 2929:2929 \
  --memory=512m \
  --cpus=1.0 \
  -e JOB_TIMEOUT=300 \
  -e JOB_RLIMIT_AS_MB=400 \
  -e JOB_RLIMIT_CPU_SECONDS=240 \
  ghcr.io/wikid82/researcharr:latest
```

Notes:
- `--memory` and `--cpus` are Docker runtime limits enforced by the
  container runtime. Use them to prevent a misbehaving job from exhausting
  host resources.
- `JOB_RLIMIT_AS_MB` and `JOB_RLIMIT_CPU_SECONDS` provide *additional*
  protection inside the container on Unix-like systems.

Docker Compose example

```yaml
version: '3.8'
services:
  researcharr:
    image: ghcr.io/wikid82/researcharr:latest
    container_name: researcharr
    ports:
      - "2929:2929"
    volumes:
      - /path/to/config:/config
    environment:
      JOB_TIMEOUT: "300"
      JOB_RLIMIT_AS_MB: "400"
      JOB_RLIMIT_CPU_SECONDS: "240"
    deploy:
      resources:
        limits:
          cpus: '1.00'
          memory: 512M
```

Kubernetes (Deployment snippet)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: researcharr
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: researcharr
          image: ghcr.io/wikid82/researcharr:latest
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "1"
          env:
            - name: JOB_TIMEOUT
              value: "300"
            - name: JOB_RLIMIT_AS_MB
              value: "400"
            - name: JOB_RLIMIT_CPU_SECONDS
              value: "240"
```

Operational guidance

- Start with conservative `--memory` and `--cpus` settings and monitor the
  job runs and memory usage. Increase limits only if necessary.
- Use `JOB_TIMEOUT` to ensure long-running or hung jobs are killed and do
  not consume resources indefinitely.
- `RUN_JOB_CONCURRENCY=1` is the safest default for single-instance
  deployments. Increase only if you explicitly want concurrent runs.

Image variants

The project publishes two primary runtime variants built from the same multistage `Dockerfile`:

- `ghcr.io/wikid82/researcharr:prod` — production image based on Debian-slim (recommended for operators).
- `ghcr.io/wikid82/researcharr:dev` — developer/debug image (same base as `prod` but with extra debugging tools installed).

Production deploy example (prod):

```bash
docker run -d \
  --name researcharr \
  -v /path/to/config:/config \
  -p 2929:2929 \
  --restart unless-stopped \
  ghcr.io/wikid82/researcharr:prod
```

Developer example (run debug image with shell):

```bash
docker run --rm -it \
  -v "$(pwd)":/app -w /app \
  -v /path/to/config:/config \
  -p 2929:2929 \
  ghcr.io/wikid82/researcharr:dev /bin/bash
```
See `docs/Environment-Variables.md` for the full list of environment
variables and their defaults.

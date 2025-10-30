## Multi-stage build
## Builder stage: install build dependencies and install Python packages into /install
FROM python:3.13-slim AS builder

# Build-time metadata (set these from CI)
ARG BUILD_VERSION=dev
ARG BUILD_NUMBER=0
ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.version=$BUILD_VERSION \
	org.opencontainers.image.revision=$GIT_SHA \
	org.opencontainers.image.created=$BUILD_DATE

WORKDIR /app

# Copy requirements and install build deps required for wheels
COPY requirements.txt /app/requirements.txt
RUN apt-get update && \
	DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
		build-essential \
		gcc \
		libssl-dev \
		libffi-dev \
		libpq-dev \
		zlib1g-dev \
		libjpeg-dev \
	&& rm -rf /var/lib/apt/lists/*

# Install Python runtime deps into an isolated prefix to copy later
RUN python -m pip install --upgrade pip setuptools wheel && \
	python -m pip install --no-cache-dir --prefix=/install -r /app/requirements.txt

# Copy the app source so it's available to later stages
COPY . /app

### Runtime stage: minimal runtime built from the same base (Debian slim)
FROM python:3.13-slim AS runtime
ARG BUILD_VERSION=dev
ARG BUILD_NUMBER=0
ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.version=$BUILD_VERSION \
	org.opencontainers.image.revision=$GIT_SHA \
	org.opencontainers.image.created=$BUILD_DATE

ENV RESEARCHARR_VERSION=$BUILD_VERSION
EXPOSE 2929

WORKDIR /app

# Install minimal runtime packages
RUN apt-get update && \
	DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
		ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from the builder
COPY --from=builder /install /usr/local
# Copy app files
COPY --from=builder /app /app

# Keep a baked copy of the application in the image so development containers
# that mount an empty host directory into /app can be auto-populated at start.
RUN mkdir -p /opt/researcharr_baked && cp -a /app/. /opt/researcharr_baked || true

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create config dir and runtime file
RUN mkdir -p /config && touch /config/cron.log

# Create a non-root user and ensure ownership of runtime dirs
## Allow overriding the runtime UID/GID at build time so images can be aligned
## with developer host UIDs (default 1000:1000). Use build args when building
## the image: `docker build --build-arg RUNTIME_UID=1000 --build-arg RUNTIME_GID=1000 .`
ARG RUNTIME_UID=1000
ARG RUNTIME_GID=1000

# Create group/user with the requested numeric IDs; if a group/user already
# exists with the same name we attempt a safe skip. Finally ensure ownership
# of directories is set to the requested UID/GID.
RUN set -eux; \
	if ! getent group researcharr >/dev/null 2>&1; then \
		groupadd -g "${RUNTIME_GID}" researcharr || true; \
	fi; \
	if ! id -u researcharr >/dev/null 2>&1; then \
		useradd -u "${RUNTIME_UID}" -g researcharr -m -d /home/researcharr -s /bin/sh researcharr || true; \
	fi; \
	chown -R "${RUNTIME_UID}":"${RUNTIME_GID}" /app /config || true

# Keep the image running the entrypoint as root so the entrypoint can
# apply runtime PUID/PGID changes to bind-mounted directories and then
# drop privileges into the configured user. The entrypoint script will
# perform the UID/GID mapping at container start.

# Write build info
RUN printf '%s\n' "version=${BUILD_VERSION}" "build=${BUILD_NUMBER}" "sha=${GIT_SHA}" > /app/VERSION

ENTRYPOINT ["/entrypoint.sh"]

### Debug stage: same runtime but with developer tooling
FROM runtime AS debug
# Install debugging utilities and development-only Python packages as root,
# then switch back to the non-root runtime user. This ensures the debug
# image contains dev tooling (debugpy, linters, etc.) without adding them
# to the minimal runtime image.
USER root
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
		bash procps iproute2 strace vim less && rm -rf /var/lib/apt/lists/*
# If a `requirements-dev.txt` is present in the project, install it into the
# image so debugpy and other dev tools are available in the debug image.
RUN python -m pip install --upgrade pip setuptools wheel || true
RUN if [ -f /app/requirements-dev.txt ]; then \
			python -m pip install --no-cache-dir -r /app/requirements-dev.txt || true; \
		else \
			python -m pip install --no-cache-dir debugpy || true; \
		fi
USER researcharr

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

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create config dir and runtime file
RUN mkdir -p /config && touch /config/cron.log

# Create a non-root user and ensure ownership of runtime dirs
RUN groupadd -r researcharr || true && useradd -r -g researcharr researcharr || true && \
	chown -R researcharr:researcharr /app /config || true

# Keep the image running the entrypoint as root so the entrypoint can
# apply runtime PUID/PGID changes to bind-mounted directories and then
# drop privileges into the configured user. The entrypoint script will
# perform the UID/GID mapping at container start.

# Write build info
RUN printf '%s\n' "version=${BUILD_VERSION}" "build=${BUILD_NUMBER}" "sha=${GIT_SHA}" > /app/VERSION

ENTRYPOINT ["/entrypoint.sh"]

### Debug stage: same runtime but with developer tooling
FROM runtime AS debug
# Install debugging utilities as root, then switch back to non-root
USER root
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
	bash procps iproute2 strace vim less && rm -rf /var/lib/apt/lists/*
USER researcharr

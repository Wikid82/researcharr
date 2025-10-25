FROM python:3.13-slim

# Build-time metadata (set these from CI)
ARG BUILD_VERSION=dev
ARG BUILD_NUMBER=0
ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.version=$BUILD_VERSION \
	org.opencontainers.image.revision=$GIT_SHA \
	org.opencontainers.image.created=$BUILD_DATE

# Expose a simple env for legacy consumers (keeps backwards compatibility)
ENV RESEARCHARR_VERSION=$BUILD_VERSION
EXPOSE 2929

## No system packages required for scheduling; we rely on Python for
## config parsing inside the entrypoint to keep the image minimal.

WORKDIR /app

COPY requirements.txt /app/requirements.txt
# Refresh and upgrade OS packages to reduce base-image CVEs, then install Python deps
# Note: this increases build time and image size slightly but reduces outdated OS package CVEs
RUN apt-get update && \
	DEBIAN_FRONTEND=noninteractive apt-get upgrade -y && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

# Use the python -m pip module and install from requirements with no cache
RUN python -m pip install --upgrade pip setuptools wheel && \
	python -m pip install --no-cache-dir -r /app/requirements.txt

# Copy application source after dependencies are installed
COPY . /app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir /config
RUN touch /config/cron.log

# Write a small build info file the running container can expose via an
# HTTP endpoint. CI should pass BUILD_VERSION, BUILD_NUMBER, and GIT_SHA.
RUN printf '%s\n' "version=${BUILD_VERSION}" "build=${BUILD_NUMBER}" "sha=${GIT_SHA}" > /app/VERSION

ENTRYPOINT ["/entrypoint.sh"]
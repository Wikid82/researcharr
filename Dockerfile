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

COPY . /app

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pyyaml

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir /config
RUN touch /config/cron.log

# Write a small build info file the running container can expose via an
# HTTP endpoint. CI should pass BUILD_VERSION, BUILD_NUMBER, and GIT_SHA.
RUN printf '%s\n' "version=${BUILD_VERSION}" "build=${BUILD_NUMBER}" "sha=${GIT_SHA}" > /app/VERSION

ENTRYPOINT ["/entrypoint.sh"]
FROM python:3.13-slim
ARG BUILD_DATE
LABEL org.opencontainers.image.created=$BUILD_DATE
ENV RESEARCHARR_VERSION=$BUILD_DATE
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

ENTRYPOINT ["/entrypoint.sh"]
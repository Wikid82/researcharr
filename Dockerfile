FROM python:3.13-slim
ARG BUILD_DATE
LABEL org.opencontainers.image.created=$BUILD_DATE
ENV RESEARCHARR_VERSION=$BUILD_DATE
EXPOSE 2929

RUN apt-get update && \
    apt-get install -y yq && \
    rm -rf /var/lib/apt/lists/*

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
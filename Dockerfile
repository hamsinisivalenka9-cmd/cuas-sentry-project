# CUAS Sentry -- packages the existing, unmodified application
# (ETL -> SQLite -> SQL analytics -> Streamlit dashboard). This file
# does not change any application behavior; it only builds the
# environment the app already runs in locally.
#
# Build:  docker build -t cuas-sentry .
# Run:    docker compose up --build   (see docker-compose.yml)

FROM python:3.12-slim

WORKDIR /app

# Dependencies first, copied and installed before the rest of the
# application code, so Docker can cache this layer -- a code change
# doesn't force a dependency reinstall, only a requirements.txt change
# does.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code. The source MCAP file and any generated SQLite
# database are excluded via .dockerignore and are never copied into
# the image -- they are provided at runtime through the
# ./data:/app/data bind mount defined in docker-compose.yml.
COPY . .
RUN chmod +x scripts/docker-entrypoint.sh

# Streamlit's default port.
EXPOSE 8501

# See scripts/docker-entrypoint.sh for the exact startup sequence.
ENTRYPOINT ["scripts/docker-entrypoint.sh"]

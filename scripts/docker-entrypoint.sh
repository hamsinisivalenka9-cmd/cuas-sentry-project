#!/bin/sh
# Container startup script.
#
# 1. Fail fast, with a clear message, if the source MCAP file isn't
#    present on the host-mounted data directory.
# 2. Build or validate the database by calling the existing, unchanged
#    scripts/build_database.py with no flags -- that script already
#    does exactly the right thing on its own: build fresh if the
#    database is missing/empty, or just validate and exit 0 if it
#    already exists and is complete. No new "does it exist" logic is
#    introduced here.
# 3. Start the dashboard, bound to 0.0.0.0 so it's reachable from the
#    host through the published port.
#
# set -e: any failure below (missing MCAP, failed build, failed
# validation) stops the container immediately with a non-zero exit
# code -- failures are never hidden.
set -e

MCAP_PATH="data/input/sanitized.mcap"

if [ ! -f "$MCAP_PATH" ]; then
    echo "ERROR: source MCAP file not found at $MCAP_PATH" >&2
    echo "Place sanitized.mcap on the host at data/input/sanitized.mcap (it is bind-mounted into the container via ./data:/app/data), then re-run 'docker compose up'." >&2
    exit 1
fi

echo "Building the database if needed, or validating it if it already exists..."
python scripts/build_database.py

echo "Starting the Streamlit dashboard at http://0.0.0.0:8501 ..."
exec streamlit run dashboard/app.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true

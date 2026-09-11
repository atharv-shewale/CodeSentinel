#!/usr/bin/env bash
# Run CodeSentinel local development stack
set -e

echo "[CodeSentinel] Starting full development stack via Docker Compose..."
docker compose up --build

#!/usr/bin/env bash
# Initialize PostgreSQL and Neo4j databases for CodeSentinel
set -e

echo "[CodeSentinel] Initializing databases..."
docker compose up -d postgres neo4j qdrant redis

echo "[CodeSentinel] Waiting for PostgreSQL to be healthy..."
until docker exec codesentinel_postgres pg_isready -U codesentinel -d codesentinel_db; do
  sleep 1
done

echo "[CodeSentinel] Database infrastructure is ready."

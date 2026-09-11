#!/usr/bin/env bash
# Run PyTest contract test suite
set -e

echo "[CodeSentinel] Running Contract Validation Test Suite..."
pytest backend/tests -v --tb=short

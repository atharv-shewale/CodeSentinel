"""
CodeSentinel Backend Test Fixtures.
"""

import asyncio
import os
from pathlib import Path
import sys
import tempfile
import pytest
from fastapi.testclient import TestClient

# Ensure root workspace and backend directories are in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configure test database URL if not explicitly provided
test_db_file = os.path.join(tempfile.gettempdir(), "codesentinel_test.db")
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{test_db_file}"

from app.core.database import init_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Initialize database tables for testing session."""
    asyncio.run(init_db())
    yield


@pytest.fixture(scope="session")
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client

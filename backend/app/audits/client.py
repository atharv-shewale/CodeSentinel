"""
CodeSentinel Audits Module: External Service Client.

Consumes Module 1, 2, 3, and 4 outputs strictly via their documented REST endpoints:
- GET /api/v1/profile/{project_id} (Module 1)
- GET /api/v1/analysis/{project_id}/system-model (Module 2)
- GET /api/v1/knowledge/{project_id}/query, POST /api/v1/agents/{project_id}/ask (Module 3)
- GET /api/v1/tests/{project_id}, GET /api/v1/executions/{project_id}, GET /api/v1/failures/{project_id} (Module 4)

No direct cross-module Python imports.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid
import httpx
from app.core.logging import logger


class AuditExternalClient:
    """HTTP client consuming Modules 1-4 through documented REST contracts."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self._base_url = base_url or "http://testserver"
        self._custom_client = client

    def _get_client(self) -> httpx.AsyncClient:
        if self._custom_client is not None:
            return self._custom_client
        try:
            from app.main import app
            transport = httpx.ASGITransport(app=app)
            return httpx.AsyncClient(transport=transport, base_url=self._base_url)
        except Exception as e:
            logger.warning(f"Failed to bind ASGITransport: {e}. Falling back to default HTTP client.")
            return httpx.AsyncClient(base_url=self._base_url)

    async def get_project_profile(self, project_id: uuid.UUID | str) -> Optional[Dict[str, Any]]:
        """Fetch project profile from Module 1 (GET /api/v1/profile/{project_id})."""
        client = self._get_client()
        should_close = self._custom_client is None
        try:
            resp = await client.get(f"/api/v1/profile/{project_id}", timeout=20.0)
            if resp.status_code == 200:
                body = resp.json()
                return body.get("data") if isinstance(body, dict) and "data" in body else body
            return None
        except Exception as e:
            logger.warning(f"Error fetching profile for project {project_id}: {e}")
            return None
        finally:
            if should_close:
                await client.aclose()

    async def get_system_model(self, project_id: uuid.UUID | str) -> Optional[Dict[str, Any]]:
        """Fetch system model from Module 2 (GET /api/v1/analysis/{project_id}/system-model)."""
        client = self._get_client()
        should_close = self._custom_client is None
        try:
            resp = await client.get(f"/api/v1/analysis/{project_id}/system-model", timeout=30.0)
            if resp.status_code == 200:
                body = resp.json()
                return body.get("data") if isinstance(body, dict) and "data" in body else body
            return None
        except Exception as e:
            logger.warning(f"Error fetching system model for project {project_id}: {e}")
            return None
        finally:
            if should_close:
                await client.aclose()

    async def get_tests(self, project_id: uuid.UUID | str) -> List[Dict[str, Any]]:
        """Fetch test cases from Module 4 (GET /api/v1/tests/{project_id})."""
        client = self._get_client()
        should_close = self._custom_client is None
        try:
            resp = await client.get(f"/api/v1/tests/{project_id}", timeout=20.0)
            if resp.status_code == 200:
                body = resp.json()
                data = body.get("data") if isinstance(body, dict) and "data" in body else body
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            logger.warning(f"Error fetching tests for project {project_id}: {e}")
            return []
        finally:
            if should_close:
                await client.aclose()

    async def get_executions(self, project_id: uuid.UUID | str) -> List[Dict[str, Any]]:
        """Fetch test executions from Module 4 (GET /api/v1/executions/project/{project_id})."""
        client = self._get_client()
        should_close = self._custom_client is None
        try:
            resp = await client.get(f"/api/v1/executions/project/{project_id}", timeout=20.0)
            if resp.status_code == 200:
                body = resp.json()
                data = body.get("data") if isinstance(body, dict) and "data" in body else body
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            logger.warning(f"Error fetching executions for project {project_id}: {e}")
            return []
        finally:
            if should_close:
                await client.aclose()

    async def get_failures(self, project_id: uuid.UUID | str) -> List[Dict[str, Any]]:
        """Fetch failures from Module 4 (GET /api/v1/failures/{project_id})."""
        client = self._get_client()
        should_close = self._custom_client is None
        try:
            resp = await client.get(f"/api/v1/failures/{project_id}", timeout=20.0)
            if resp.status_code == 200:
                body = resp.json()
                data = body.get("data") if isinstance(body, dict) and "data" in body else body
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            logger.warning(f"Error fetching failures for project {project_id}: {e}")
            return []
        finally:
            if should_close:
                await client.aclose()

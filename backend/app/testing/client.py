"""
CodeSentinel Testing Module: External Service HTTP Client.

Consumes Module 2 and Module 3 outputs strictly via their documented REST endpoints.
Does NOT import directly from analyzer, requirements, knowledge_graph, rag, or agents.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import uuid
import httpx
from app.core.logging import logger


class ExternalServiceClient:
    """HTTP Client consuming external modules via documented REST endpoints."""

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

        # In-process ASGI transport allows calling the app without circular dependencies
        try:
            from app.main import app
            transport = httpx.ASGITransport(app=app)
            return httpx.AsyncClient(transport=transport, base_url=self._base_url)
        except Exception as e:
            logger.warning(f"Failed to bind ASGITransport to app: {e}. Falling back to network client.")
            return httpx.AsyncClient(base_url=self._base_url)

    async def get_system_model(self, project_id: uuid.UUID | str) -> Optional[Dict[str, Any]]:
        """
        Fetch Software System Model from Module 2.
        Endpoint: GET /api/v1/analysis/{project_id}/system-model
        """
        url = f"/api/v1/analysis/{project_id}/system-model"
        client = self._get_client()
        should_close = self._custom_client is None

        try:
            resp = await client.get(url, timeout=30.0)
            if resp.status_code == 200:
                body = resp.json()
                # Unwrap APIResponse envelope
                if isinstance(body, dict) and "data" in body and body.get("success"):
                    return body["data"]
                return body
            elif resp.status_code == 404:
                logger.info(f"System model not found for project {project_id}")
                return None
            else:
                logger.warning(f"Error fetching system model {project_id}: HTTP {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to query system model endpoint for {project_id}: {e}")
            return None
        finally:
            if should_close:
                await client.aclose()

    async def ask_agent(
        self,
        project_id: uuid.UUID | str,
        agent_type: str,
        question: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Query AI Agent from Module 3.
        Endpoint: POST /api/v1/agents/{project_id}/ask
        """
        url = f"/api/v1/agents/{project_id}/ask"
        payload = {
            "agent_type": agent_type,
            "question": question,
            "context": context or {},
        }
        client = self._get_client()
        should_close = self._custom_client is None

        try:
            resp = await client.post(url, json=payload, timeout=60.0)
            if resp.status_code == 200:
                body = resp.json()
                if isinstance(body, dict) and "data" in body and body.get("success"):
                    return body["data"]
                return body
            else:
                logger.warning(f"Agent request failed ({agent_type}) for project {project_id}: HTTP {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Failed to query agent endpoint for {project_id}: {e}")
            return None
        finally:
            if should_close:
                await client.aclose()

    async def query_knowledge_graph(
        self,
        project_id: uuid.UUID | str,
        query_type: str,
        target_name: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Query Knowledge Graph from Module 3.
        Endpoint: GET /api/v1/knowledge/{project_id}/query
        """
        url = f"/api/v1/knowledge/{project_id}/query"
        params: Dict[str, str] = {"query_type": query_type}
        if target_name:
            params["target_name"] = target_name

        client = self._get_client()
        should_close = self._custom_client is None

        try:
            resp = await client.get(url, params=params, timeout=30.0)
            if resp.status_code == 200:
                body = resp.json()
                if isinstance(body, dict) and "data" in body and body.get("success"):
                    return body["data"]
                return body
            return None
        except Exception as e:
            logger.error(f"Failed to query knowledge graph endpoint for {project_id}: {e}")
            return None
        finally:
            if should_close:
                await client.aclose()

    async def trigger_knowledge_graph_build(self, project_id: uuid.UUID | str) -> bool:
        """
        Trigger Knowledge Graph incremental build in Module 3.
        Endpoint: POST /api/v1/knowledge/{project_id}/build
        """
        url = f"/api/v1/knowledge/{project_id}/build"
        client = self._get_client()
        should_close = self._custom_client is None

        try:
            resp = await client.post(url, timeout=30.0)
            return resp.status_code in (200, 201, 202)
        except Exception as e:
            logger.error(f"Failed to trigger knowledge build for {project_id}: {e}")
            return False
        finally:
            if should_close:
                await client.aclose()

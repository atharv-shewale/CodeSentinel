"""
CodeSentinel Backend: API v1 Central Router Aggregation.

Mounts all modular routers under standard /api/v1 prefixes.
"""

from fastapi import APIRouter

# Import endpoints and module routers
from app.agents.router import router as agents_router
from app.analytics.router import router as analytics_router
from app.analyzer.router import router as analyzer_router
from app.api.v1.endpoints.assistant import router as assistant_router
from app.api.v1.endpoints.jobs import router as jobs_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.reports import router as reports_router
from app.audits.router import router as audits_router
from app.failures.router import router as failures_router
from app.ingestion.router import router as repositories_router
from app.knowledge_graph.router import router as knowledge_router
from app.profiler.router import router as profile_router
from app.rag.router import router as rag_router
from app.requirements.router import router as requirements_router
from app.sandbox.router import router as executions_router
from app.testing.router import router as tests_router

api_v1_router = APIRouter()

# 1. Projects
api_v1_router.include_router(projects_router, prefix="/projects", tags=["Projects"])

# 2. Repositories / Ingestion
api_v1_router.include_router(repositories_router, prefix="/repositories", tags=["Repositories"])

# 3. Requirements
api_v1_router.include_router(requirements_router, prefix="/requirements", tags=["Requirements"])

# 4. Profile
api_v1_router.include_router(profile_router, prefix="/profile", tags=["Profiler"])

# 5. Analysis (AST / Tree-sitter)
api_v1_router.include_router(analyzer_router, prefix="/analysis", tags=["Analyzer"])

# 6. Knowledge Graph (Neo4j)
api_v1_router.include_router(knowledge_router, prefix="/knowledge", tags=["Knowledge Graph"])

# 7. RAG (Vector Embeddings & Qdrant)
api_v1_router.include_router(rag_router, prefix="/rag", tags=["RAG"])

# 8. Agents (LangGraph Orchestration)
api_v1_router.include_router(agents_router, prefix="/agents", tags=["Agents"])

# 9. Tests (TestCases with Provenance)
api_v1_router.include_router(tests_router, prefix="/tests", tags=["Tests"])

# 10. Executions (Sandbox Runs)
api_v1_router.include_router(executions_router, prefix="/executions", tags=["Executions"])

# 11. Failures (RCA & Triage)
api_v1_router.include_router(failures_router, prefix="/failures", tags=["Failures"])

# 12. Audits (Quality & Security)
api_v1_router.include_router(audits_router, prefix="/audits", tags=["Audits"])

# 13. Analytics (Health & Metrics)
api_v1_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])

# 14. Reports
api_v1_router.include_router(reports_router, prefix="/reports", tags=["Reports"])

# 15. Assistant
api_v1_router.include_router(assistant_router, prefix="/assistant", tags=["Assistant"])

# 16. Background Jobs (Status & Telemetry)
api_v1_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])

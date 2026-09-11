# API Architecture & Contract Specification - CodeSentinel

## 1. REST Conventions & Envelope
All responses return HTTP status codes aligned with REST semantics and payloads wrapped in:

```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": { ... },
  "error": null,
  "pagination": null,
  "timestamp": "2026-09-02T12:00:00Z"
}
```

## 2. Route Groups Summary

| Endpoint Group | Tag | Description |
| :--- | :--- | :--- |
| `/api/v1/projects` | Projects | Repository onboarding and metadata management |
| `/api/v1/repositories` | Repositories | Git cloning, branch tracking, and synchronization |
| `/api/v1/requirements` | Requirements | Specs, acceptance criteria, and traceability linkages |
| `/api/v1/profile` | Profiler | Codebase language profiling and metrics |
| `/api/v1/analysis` | Analyzer | AST Tree-sitter decomposition & route extraction |
| `/api/v1/knowledge` | Knowledge Graph | Neo4j relationship queries and impact graphs |
| `/api/v1/rag` | RAG | Qdrant semantic search and vector indexing |
| `/api/v1/agents` | Agents | LangGraph multi-agent execution workflows |
| `/api/v1/tests` | Tests | TestCases with mandatory Provenance enum |
| `/api/v1/executions` | Executions | Isolated Docker sandbox test suite runs |
| `/api/v1/failures` | Failures | Recorded defects, triage, and Root Cause Analysis |
| `/api/v1/audits` | Audits | OWASP vulnerabilities and code quality findings |
| `/api/v1/analytics` | Analytics | Health score and quality metrics overview |
| `/api/v1/reports` | Reports | Executive summary and compliance reports |
| `/api/v1/assistant` | Assistant | Context-aware AI chat and action suggestions |
| `/api/v1/jobs` | Jobs | Background job status polling (`GET /jobs/{job_id}`) |

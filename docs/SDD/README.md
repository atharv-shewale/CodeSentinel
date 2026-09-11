# Software Design Document (SDD) - CodeSentinel

## 1. System Architecture
CodeSentinel employs a decoupled micro-modular architecture built around frozen Pydantic contracts.

### Component Layering
```
+-------------------------------------------------------------------+
|                        Frontend (React + Vite)                   |
|                        TypeScript Mirror Types                    |
+-------------------------------------------------------------------+
                                   | HTTP / WebSocket
+-------------------------------------------------------------------+
|                        FastAPI Gateway (v1)                       |
|           Universal APIResponse[T] Envelope Serialization         |
+-------------------------------------------------------------------+
   |                 |               |               |
+------------+ +------------+ +------------+ +------------+
| Ingestion  | | Profiler   | | Analyzer   | | Agents     |
| & Git      | | AST Parser | | Knowledge  | | LangGraph  |
+------------+ +------------+ +------------+ +------------+
       |             |               |               |
+-------------------------------------------------------------------+
|                Shared Contract Layer (shared/schemas/)            |
|    Project, Requirement, CodeEntity, APIRoute, TestCase,          |
|    TestExecution, Failure, AuditFinding, JobStatus                |
+-------------------------------------------------------------------+
   |                 |               |               |
+------------+ +------------+ +------------+ +------------+
| PostgreSQL | | Neo4j      | | Qdrant     | | Redis      |
| (Primary)  | | (Graph)    | | (Vectors)  | | (Jobs)     |
+------------+ +------------+ +------------+ +------------+
```

## 2. Data Stores & Responsibilities
- **PostgreSQL**: Primary transactional persistence for Projects, Requirements, TestCases, Executions, Failures, and Audits.
- **Neo4j**: Relationships ONLY (e.g. `(Requirement)-[:VERIFIED_BY]->(TestCase)`, `(APIRoute)-[:HANDLED_BY]->(CodeEntity)`).
- **Qdrant**: High-dimensional vector embeddings for code retrieval and semantic RAG.
- **Redis**: Asynchronous task queues and real-time job status streaming.

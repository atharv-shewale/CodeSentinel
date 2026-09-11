# Software Requirements Specification (SRS) - CodeSentinel

## 1. Introduction
CodeSentinel is an AI-powered software engineering intelligence platform. It analyzes codebases using static AST extraction, knowledge graphs, and vector search, automatically deriving and verifying tests against requirements with end-to-end provenance guarantees.

## 2. System Scope & Core Modules
1. **Repository Ingestion & Profiling**: Parse Git repositories, track branches, and map structural entities.
2. **AST & Syntax Analysis**: Tree-sitter powered semantic AST decomposition into files, classes, functions, and methods.
3. **Knowledge Graph Engine (Neo4j)**: Graph relationships between code entities, API routes, and requirement specs.
4. **Vector Retrieval & RAG (Qdrant)**: Dense semantic search across code snippets, docstrings, and failure logs.
5. **Multi-Agent Orchestration (LangGraph)**: Stateful autonomous agents for test case synthesis, failure triage, and audit remediation.
6. **Isolated Sandbox Execution**: Ephemeral Docker sandboxes executing test suites and measuring branch/line coverage.
7. **Failure Root Cause Analysis**: Automated diagnostics, stack trace triaging, and code fix synthesis.

## 3. Mandatory Contract Invariants
- **TestCase Provenance**: Every synthesized test MUST specify its origin via `TestProvenance` (`REQUIREMENT_VERIFIED`, `SCHEMA_DERIVED`, `COVERAGE_ONLY`, `AI_INFERRED`).
- **Response Envelope**: All API endpoints MUST return responses wrapped in the universal `APIResponse[T]` envelope.
- **Shared Schemas**: Modules interact strictly via `shared/schemas/` models. Internal module models are private.

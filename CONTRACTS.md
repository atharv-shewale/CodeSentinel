# CodeSentinel Contract Specification (Phase 0 Frozen Contracts)

> **Status:** FROZEN & LOCKED  
> **Target Audience:** Independent Module Engineers (Modules 1–5), QA, and Architecture Team  
> **Scope:** Shared Pydantic Schemas, Response Envelopes, API Route Catalog, and Job Protocols  

---

## 1. Architectural Philosophy & Developer Rules

CodeSentinel is an AI-powered software engineering intelligence platform. To allow 5 independent development teams to build separate modules in parallel without merge conflicts or cross-boundary coupling, the following rules are **strictly enforced**:

1. **The Shared Contract Rule:**
   All shared domain models live in `shared/schemas/`. **No module may import another module's internal code or schemas directly.** Any data exchanged across API routes or worker queues must use models exported by `shared.schemas`.
2. **The Universal Envelope Rule:**
   Every single HTTP endpoint in CodeSentinel returns data wrapped in the `APIResponse[T]` envelope. Direct raw responses or inconsistent error JSON structures are forbidden.
3. **The Test Provenance Invariant:**
   Every test case synthesized or ingested into CodeSentinel must have an explicit `provenance` tag. This field is mandatory and determines execution prioritization, test trust, and compliance reporting.
4. **Isolated Sandbox Boundary:**
   Test executions happen in ephemeral Docker sandbox containers. Sandbox infrastructure is completely isolated from production application containers and databases.

---

## 2. Universal API Response Envelope

All endpoints produce JSON formatted according to `APIResponse[T]`.

### Success Response Format
```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": { ... },
  "error": null,
  "pagination": {
    "total": 120,
    "page": 1,
    "page_size": 20,
    "total_pages": 6,
    "has_next": true,
    "has_prev": false
  },
  "timestamp": "2026-09-02T12:00:00.000000Z"
}
```

### Error Response Format
```json
{
  "success": false,
  "message": "Request validation failed.",
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request payload failed schema validation.",
    "details": {
      "errors": [
        {
          "loc": ["body", "provenance"],
          "msg": "Field required",
          "type": "missing"
        }
      ]
    },
    "trace_id": "req-892bf3"
  },
  "pagination": null,
  "timestamp": "2026-09-02T12:00:00.000000Z"
}
```

---

## 3. Shared Domain Schemas (`shared/schemas/`)

### 3.1 `Project` (`shared/schemas/project.py`)
Root container representing an onboarded software codebase.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Auto (UUIDv4) | Unique project identifier. |
| `name` | `str` (1-128 chars) | Yes | Human-readable project title. |
| `description` | `Optional[str]` | No | Optional overview of codebase purpose. |
| `repository_url` | `str` | Yes | Git remote URL or file path. |
| `default_branch` | `str` | Default `"main"` | Default branch for continuous analysis. |
| `provider` | `RepoProvider` | Default `GITHUB` | `GITHUB`, `GITLAB`, `BITBUCKET`, `LOCAL`. |
| `tags` | `List[str]` | Default `[]` | Categorization and organizational tags. |
| `status` | `ProjectStatus` | Default `INITIALIZING` | `INITIALIZING`, `ACTIVE`, `INDEXING`, `ANALYZING`, `READY`, `FAILED`, `ARCHIVED`. |
| `last_indexed_commit` | `Optional[str]` | No | Git SHA-1 of latest processed commit. |
| `total_files` | `int` | Default `0` | Total parsed source files. |
| `total_lines_of_code` | `int` | Default `0` | Total executable lines of code (LOC). |
| `created_at` | `datetime` | Auto (UTC) | Creation timestamp. |
| `updated_at` | `datetime` | Auto (UTC) | Last modified timestamp. |

---

### 3.2 `Requirement` (`shared/schemas/requirement.py`)
Functional and non-functional specifications driving requirement-verified test generation.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Auto (UUIDv4) | Unique requirement identifier. |
| `project_id` | `UUID` | Yes | Associated project UUID. |
| `identifier` | `str` | Yes | Business identifier (e.g. `REQ-AUTH-001`). |
| `title` | `str` (1-256 chars) | Yes | Concise requirement title. |
| `description` | `str` | Yes | Comprehensive behavior specification. |
| `req_type` | `RequirementType` | Default `FUNCTIONAL` | `FUNCTIONAL`, `NON_FUNCTIONAL`, `SECURITY`, `PERFORMANCE`, `API_CONTRACT`, `COMPLIANCE`. |
| `priority` | `RequirementPriority` | Default `MEDIUM` | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`. |
| `status` | `RequirementStatus` | Default `DRAFT` | `DRAFT`, `APPROVED`, `IMPLEMENTED`, `VERIFIED`, `FAILED`, `DEPRECATED`. |
| `acceptance_criteria` | `List[str]` | Default `[]` | List of verifiable acceptance test conditions. |
| `linked_entity_ids` | `List[UUID]` | Default `[]` | UUIDs of code entities implementing this spec. |
| `verification_coverage_pct` | `float` (0.0-100.0) | Default `0.0` | Calculated verified test coverage percentage. |

---

### 3.3 `CodeEntity` (`shared/schemas/code_entity.py`)
Structural AST atom extracted via Tree-sitter.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Auto (UUIDv4) | Unique entity identifier. |
| `project_id` | `UUID` | Yes | Associated project UUID. |
| `name` | `str` | Yes | Symbol name (e.g. `authenticate_user`). |
| `qualified_name` | `str` | Yes | Full canonical path (`app.services.auth.authenticate_user`). |
| `entity_type` | `EntityType` | Yes | `FILE`, `MODULE`, `CLASS`, `FUNCTION`, `METHOD`, `INTERFACE`, `TYPE_ALIAS`, `VARIABLE`. |
| `language` | `str` | Yes | Language name (e.g. `python`, `typescript`). |
| `location` | `CodeLocation` | Yes | File path, start line, end line, column offsets. |
| `parent_entity_id` | `Optional[UUID]` | No | Enclosing class or module UUID. |
| `docstring` | `Optional[str]` | No | Extracted documentation string. |
| `source_code` | `Optional[str]` | No | Raw source code snippet. |
| `parameters` | `List[CodeParameter]` | Default `[]` | List of typed function parameters. |
| `return_type` | `Optional[str]` | No | Return type annotation. |
| `visibility` | `Visibility` | Default `PUBLIC` | `PUBLIC`, `PROTECTED`, `PRIVATE`, `INTERNAL`. |
| `complexity_score` | `Optional[float]` | No | Cyclomatic / cognitive complexity score. |
| `ast_hash` | `Optional[str]` | No | Cryptographic AST hash for change tracking. |
| `embedding_id` | `Optional[str]` | No | Qdrant vector point ID. |

---

### 3.4 `APIRoute` (`shared/schemas/api_route.py`)
Discovered and analyzed HTTP endpoint contracts.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Auto (UUIDv4) | Unique route identifier. |
| `project_id` | `UUID` | Yes | Associated project UUID. |
| `code_entity_id` | `Optional[UUID]` | No | UUID of controller function/handler. |
| `path` | `str` | Yes | URL pattern path (e.g. `/api/v1/users/{id}`). |
| `http_method` | `HTTPMethod` | Yes | `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `OPTIONS`, `HEAD`. |
| `summary` | `Optional[str]` | No | Short endpoint summary. |
| `auth_requirement` | `AuthRequirement` | Default `NONE` | `NONE`, `BEARER_TOKEN`, `API_KEY`, `OAUTH2`, `BASIC`, `CUSTOM`. |
| `parameters` | `List[RouteParameter]` | Default `[]` | Parameter definitions (PATH, QUERY, HEADER, BODY). |
| `request_body_schema` | `Optional[Dict]` | No | JSON schema for request body. |
| `response_schemas` | `Dict[str, Any]` | Default `{}` | Status code to response JSON schema mapping. |

---

### 3.5 `TestCase` (`shared/schemas/test_case.py`)
Executable test artifact with mandatory provenance tracking.

> [!IMPORTANT]
> The `provenance` field is **mandatory**. It establishes downstream verification confidence:
> - `REQUIREMENT_VERIFIED`: Test synthesized directly from an approved business Requirement spec.
> - `SCHEMA_DERIVED`: Test synthesized from OpenAPI definitions or AST function signatures.
> - `COVERAGE_ONLY`: Test synthesized to execute uncovered AST branches/lines.
> - `AI_INFERRED`: Test inferred by LLM heuristics from historical failure patterns and edge cases.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Auto (UUIDv4) | Unique test case identifier. |
| `project_id` | `UUID` | Yes | Associated project UUID. |
| `name` | `str` (1-256 chars) | Yes | Function name of the test (e.g. `test_login_success`). |
| `description` | `str` | Yes | Human description of the test scenario. |
| `test_type` | `TestType` | Default `UNIT` | `UNIT`, `INTEGRATION`, `E2E`, `PROPERTY_BASED`, `MUTATION`, `SECURITY`, `PERFORMANCE`, `API_CONTRACT`. |
| `provenance` | `TestProvenance` | **MANDATORY** | `REQUIREMENT_VERIFIED`, `SCHEMA_DERIVED`, `COVERAGE_ONLY`, `AI_INFERRED`. |
| `target_entity_id` | `Optional[UUID]` | No | CodeEntity being tested. |
| `requirement_id` | `Optional[UUID]` | No | Requirement being verified (if REQUIREMENT_VERIFIED). |
| `file_path` | `str` | Yes | Target test file location. |
| `test_code` | `str` | Yes | Executable test implementation code. |
| `assertions` | `List[AssertionSpec]` | Default `[]` | Itemized assertion specifications. |
| `status` | `TestStatus` | Default `ACTIVE` | `ACTIVE`, `DRAFT`, `QUARANTINED`, `DEPRECATED`, `FLAKY`. |
| `flakiness_score` | `float` (0.0-1.0) | Default `0.0` | Flakiness probability metric. |

---

### 3.6 `TestExecution` (`shared/schemas/test_execution.py`)
Telemetry from isolated Docker sandbox test suite runs.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Auto (UUIDv4) | Execution run UUID. |
| `project_id` | `UUID` | Yes | Associated project UUID. |
| `environment` | `ExecutionEnvironment` | Default `DOCKER_SANDBOX` | `DOCKER_SANDBOX`, `LOCAL_PROCESS`, `KUBERNETES_JOB`. |
| `status` | `ExecutionStatus` | Default `QUEUED` | `QUEUED`, `RUNNING`, `PASSED`, `FAILED`, `ERROR`, `TIMED_OUT`, `CANCELLED`. |
| `total_tests` | `int` | Default `0` | Total test count. |
| `passed_tests` | `int` | Default `0` | Passed count. |
| `failed_tests` | `int` | Default `0` | Failed count. |
| `total_duration_ms` | `float` | Default `0.0` | Total run time in milliseconds. |
| `results` | `List[TestResultItem]` | Default `[]` | Itemized test outcomes, stdout, and tracebacks. |
| `coverage` | `Optional[CoverageMetrics]` | No | Line/branch statement coverage metrics. |

---

### 3.7 `Failure` (`shared/schemas/failure.py`)
Recorded execution defects and AI-generated Root Cause Analysis.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Auto (UUIDv4) | Unique defect identifier. |
| `project_id` | `UUID` | Yes | Associated project UUID. |
| `test_case_id` | `Optional[UUID]` | No | Failing test case UUID. |
| `title` | `str` | Yes | Brief failure summary. |
| `error_message` | `str` | Yes | Raw exception or assertion error message. |
| `stack_trace` | `Optional[str]` | No | Full runtime stack trace. |
| `category` | `FailureCategory` | Default `UNKNOWN` | `SYNTAX_ERROR`, `LOGIC_ERROR`, `SCHEMA_VIOLATION`, `ASSERTION_FAILED`, `TIMEOUT`, `NULL_POINTER_OR_NONE`, `AUTHENTICATION_FAILURE`, `ENVIRONMENT_ISSUE`, `PERFORMANCE_REGRESSION`. |
| `severity` | `FailureSeverity` | Default `MAJOR` | `BLOCKER`, `CRITICAL`, `MAJOR`, `MINOR`, `TRIVIAL`. |
| `status` | `FailureStatus` | Default `DETECTED` | `DETECTED`, `TRIAGED`, `INVESTIGATING`, `ROOT_CAUSE_IDENTIFIED`, `FIX_PROPOSED`, `RESOLVED`, `IGNORED`. |
| `root_cause` | `Optional[RootCauseAnalysis]` | No | AI Root Cause Analysis payload with suggested code fix diff. |

---

### 3.8 `AuditFinding` (`shared/schemas/audit.py`)
Static analysis, security vulnerability, and architecture drift findings.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Auto (UUIDv4) | Finding UUID. |
| `project_id` | `UUID` | Yes | Associated project UUID. |
| `rule_id` | `str` | Yes | Rule identifier (e.g. `SEC-OWASP-A03-SQLI`). |
| `title` | `str` | Yes | Concise defect title. |
| `description` | `str` | Yes | Impact and technical explanation. |
| `category` | `AuditCategory` | Default `CODE_SMELL` | `SECURITY_VULNERABILITY`, `CODE_SMELL`, `PERFORMANCE_HOTSPOT`, `API_CONTRACT_VIOLATION`, `ARCHITECTURE_DRIFT`, `TYPE_SAFETY`, `DOCUMENTATION_DEFICIT`, `COMPLIANCE_NON_CONFORMANCE`. |
| `severity` | `AuditSeverity` | Default `MEDIUM` | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`. |
| `standard` | `Optional[ComplianceStandard]` | No | `OWASP_TOP_10`, `CWE`, `SANS_TOP_25`, `PCI_DSS`, `SOC2`. |
| `location` | `CodeLocation` | Yes | File path, start/end line coordinates. |
| `remediation_suggestion` | `Optional[str]` | No | Suggested code diff or mitigation strategy. |
| `cvss_score` | `Optional[float]` (0.0-10.0) | No | CVSS vulnerability rating. |

---

## 4. Background Job Pattern (`FastAPI -> Redis -> Worker`)

Long-running tasks (ingestion, AST analysis, test generation, sandbox execution) are processed asynchronously via Redis task queues.

### Lifecycle State Machine
```
[ PENDING ] ---> [ RUNNING (0%..99%) ] ---> [ COMPLETED (100%) ]
                            |
                            +-------------> [ FAILED ]
```

### Job Polling Endpoint: `GET /api/v1/jobs/{job_id}`
Returns the standardized `JobStatus` schema:
```json
{
  "success": true,
  "message": "Job status is RUNNING (50.0% complete).",
  "data": {
    "job_id": "c1f7b889-42b8-4bc2-a1df-7b567a123abc",
    "job_type": "TEST_GENERATION",
    "status": "RUNNING",
    "progress": {
      "current_step": 50,
      "total_steps": 100,
      "percentage": 50.0,
      "status_message": "Generating assertions for UserService..."
    },
    "result": null,
    "error": null,
    "created_at": "2026-09-02T12:00:00Z",
    "updated_at": "2026-09-02T12:00:05Z",
    "completed_at": null
  },
  "error": null,
  "pagination": null,
  "timestamp": "2026-09-02T12:00:05Z"
}
```

---

## 5. API Route Catalog (All 16 Endpoint Groups)

| HTTP Method | Route Path | Summary | Expected Return Envelope Data |
| :--- | :--- | :--- | :--- |
| **GET** | `/api/v1/projects` | List projects | `List[Project]` |
| **POST** | `/api/v1/projects` | Create project | `Project` (HTTP 201) |
| **GET** | `/api/v1/projects/{id}` | Get project | `Project` |
| **PUT** | `/api/v1/projects/{id}` | Update project | `Project` |
| **DELETE** | `/api/v1/projects/{id}` | Delete project | `Dict` (HTTP 200) |
| **POST** | `/api/v1/repositories/ingest` | Enqueue repo clone | `JobStatus` (HTTP 202) |
| **GET** | `/api/v1/repositories/status` | Git service health | `Dict[str, Any]` |
| **POST** | `/api/v1/repositories/sync` | Sync repo changes | `JobStatus` (HTTP 202) |
| **GET** | `/api/v1/requirements` | List requirements | `List[Requirement]` |
| **POST** | `/api/v1/requirements` | Create requirement | `Requirement` (HTTP 201) |
| **GET** | `/api/v1/requirements/{id}` | Get requirement | `Requirement` |
| **PUT** | `/api/v1/requirements/{id}` | Update requirement | `Requirement` |
| **DELETE** | `/api/v1/requirements/{id}` | Delete requirement | `Dict` (HTTP 200) |
| **POST** | `/api/v1/profile/run` | Enqueue profiling | `JobStatus` (HTTP 202) |
| **GET** | `/api/v1/profile/{id}` | Get project profile | `Dict[str, Any]` |
| **POST** | `/api/v1/analysis/ast` | Enqueue AST parse | `JobStatus` (HTTP 202) |
| **GET** | `/api/v1/analysis/entities/{id}` | Get code entities | `List[CodeEntity]` |
| **GET** | `/api/v1/analysis/routes/{id}` | Get API routes | `List[APIRoute]` |
| **GET** | `/api/v1/knowledge/graph/{id}` | Get Neo4j topology | `GraphResponse` (Nodes & Edges) |
| **POST** | `/api/v1/knowledge/query` | Query graph | `Dict[str, Any]` |
| **POST** | `/api/v1/rag/search` | Qdrant semantic search | `List[RAGSearchResult]` |
| **POST** | `/api/v1/rag/index` | Enqueue vector indexing | `JobStatus` (HTTP 202) |
| **POST** | `/api/v1/agents/orchestrate` | Enqueue LangGraph run | `JobStatus` (HTTP 202) |
| **GET** | `/api/v1/agents/runs/{id}` | Get LangGraph state | `AgentRunStatus` |
| **GET** | `/api/v1/tests` | List test cases | `List[TestCase]` |
| **POST** | `/api/v1/tests` | Create test case | `TestCase` (HTTP 201) |
| **POST** | `/api/v1/tests/generate` | Enqueue test generation | `JobStatus` (HTTP 202) |
| **GET** | `/api/v1/tests/{id}` | Get test case | `TestCase` |
| **PUT** | `/api/v1/tests/{id}` | Update test case | `TestCase` |
| **POST** | `/api/v1/executions/run` | Enqueue sandbox run | `JobStatus` (HTTP 202) |
| **GET** | `/api/v1/executions/{id}` | Get execution report | `TestExecution` |
| **GET** | `/api/v1/executions/project/{id}` | List executions | `List[TestExecution]` |
| **GET** | `/api/v1/failures` | List failures | `List[Failure]` |
| **POST** | `/api/v1/failures/triage` | Enqueue AI triage & RCA | `JobStatus` (HTTP 202) |
| **GET** | `/api/v1/failures/{id}/rca` | Get RCA & fix diff | `RootCauseAnalysis` |
| **POST** | `/api/v1/audits/scan` | Enqueue security audit | `JobStatus` (HTTP 202) |
| **GET** | `/api/v1/audits/findings/{id}` | List audit findings | `List[AuditFinding]` |
| **GET** | `/api/v1/analytics/overview/{id}`| Intelligence overview | `Dict[str, Any]` (Health score, coverage) |
| **GET** | `/api/v1/analytics/metrics/{id}` | Quality metrics | `Dict[str, Any]` (MTTR, provenance split) |
| **POST** | `/api/v1/reports/generate` | Enqueue PDF/MD report | `JobStatus` (HTTP 202) |
| **GET** | `/api/v1/reports/{id}` | Get report payload | `ReportSummary` |
| **POST** | `/api/v1/assistant/chat` | Chat with AI assistant | `ChatResponse` |
| **POST** | `/api/v1/assistant/feedback`| Record user feedback | `Dict[str, str]` |
| **GET** | `/api/v1/jobs/{id}` | Background job status | `JobStatus` |
| **POST** | `/api/v1/jobs/test-job` | Dispatch test job | `JobStatus` (HTTP 202) |

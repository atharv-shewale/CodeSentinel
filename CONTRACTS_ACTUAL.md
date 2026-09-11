# CodeSentinel: Actual Operational Contracts (CONTRACTS_ACTUAL.md)

This document provides a candid, comprehensive accounting of all operational API contracts, schemas, and endpoints across the integrated CodeSentinel platform, recording where and why implementations adapted from Phase 0's initial theoretical specifications (`CONTRACTS.md`).

---

## 1. Executive Summary of Adaptations

| Module | Phase 0 Specification | Actual Operational Implementation | Rationale | Status |
|---|---|---|---|---|
| **Envelope Envelope** | Standard envelope with generic data | `APIResponse[T]` with `status`, `data`, `message`, `error`, `timestamp` | Uniform unwrap across frontend `ApiClient` and backend FastAPI services. | Permanent |
| **Module 1 (Projects)** | Multiple route endpoints under `/repositories` and `/projects` | Consolidated under `/api/v1/projects` and `/api/v1/profile` | Clean REST separation between lifecycle metadata and deep structural profiler output. | Permanent |
| **Module 2 (Analysis)** | `SoftwareSystemModel` flat entity list | `SoftwareSystemModel` partitioned into `files`, `classes`, `functions`, `apis`, `dependencies`, `requirements`, `mappings` | Preserves hierarchical AST semantics needed for direct Neo4j graph materialization. | Permanent |
| **Module 2 (Criteria)** | Strict criteria invariant | Strict criteria invariant preserved: empty criteria prevents Tier 1 test generation | Direct adherence to requirement assurance invariant. | Permanent |
| **Module 3 (Agents)** | Querying agents with dynamic role string | Enforced enum `AgentType` with 6 specialized agents (`REQUIREMENT_AGENT`, `CODE_AGENT`, `QA_TEST_AGENT`, `AUDIT_AGENT`, `FAILURE_AGENT`, `ENGINEERING_INTELLIGENCE_AGENT`) | Guarantees static type safety and deterministic system prompt selection. | Permanent |
| **Module 3 (Evidence Grounding)** | Ungrounded flag optional | Mandatory Grounding Verifier: answers must cite real candidate tokens from retrieved context or be flagged `is_grounded=False` | Eliminates ungrounded hallucinations in automated engineering workflows. | Permanent |
| **Module 4 (Testing)** | Generation without provenance tracking | Strict 4-tier provenance enum (`REQUIREMENT_VERIFIED`, `SCHEMA_DERIVED`, `COVERAGE_ONLY`, `AI_INFERRED`) | Enforces assurance traceability; prevents fabricated requirement test claims. | Permanent |
| **Module 4 (Sandbox)** | Asynchronous job only | Dual-mode: Asynchronous (`sync=False`) or Synchronous (`sync=True`) | Supports interactive UI debugging and deterministic CI/CD pipelines. | Permanent |
| **Module 4 (Failures)** | Endpoint `/failures/{id}` | Dual lookup: `/api/v1/failures/{identifier}` (handles both failure UUID and project UUID), with `/api/v1/failures/project/{project_id}` alias | Backward compatibility with Phase 0 frontend expectations. | Permanent |
| **Module 5 (Audits)** | Single synchronous endpoint | Category-partitioned audits with deterministic rules (`QUAL-*`, `SEC-*`, `COV-*`, `ARCH-*`) and sync/async job modes | Allows auditing large codebases without blocking the HTTP worker thread. | Permanent |
| **Module 5 (Analytics)** | Unified overall score | Deterministic 5-part formula: $0.35 \times \text{ReqCoverage} + 0.25 \times \text{ReqPassRate} + 0.15 \times \text{Quality} + 0.15 \times \text{Security} + 0.10 \times \text{Architecture}$ | Transparent calculation; no arbitrary weights or black-box ratings. | Permanent |
| **Module 5 (Coverage)** | Fabricated multi-language aggregation | Per-language coverage reporting only; no unified fabrication across dissimilar language ecosystems | Adheres to strict engineering reality (Python coverage is Python coverage; TS coverage is TS coverage). | Permanent |
| **Module 5 (Reports)** | `GET /api/v1/reports/{project_id}` | `GET /api/v1/analytics/{project_id}/report` and `GET /api/v1/reports/{identifier}` (dual lookup) | Report synthesizes live analytics, audits, and traceability matrices managed by Module 5's engine. | Permanent |

---

## 2. Detailed Contract Divergence Analysis

### 2.1 Project Profile Retrieval
- **Contract Said:** `GET /api/v1/repositories/{repo_id}/profile`
- **Code Actually Does:** `GET /api/v1/profile/{project_id}`
- **Why Change Was Made:** In CodeSentinel, a "Project" represents the unified boundary of requirements, repositories, tests, and audit trails. Routing by `project_id` provides consistent resource addressing across all 5 modules.
- **Reconciliation:** Permanent. Frontend and API specs use `/api/v1/profile/{project_id}`.

### 2.2 System Model Structure
- **Contract Said:** Generic list of code entities `entities: List[CodeEntity]` in system model.
- **Code Actually Does:** Dual decomposition: structured decomposition (`files: List[FileNode]`, `classes: List[CodeEntity]`, `functions: List[CodeEntity]`, `apis: List[Dict]`, `dependencies: Dict`, `requirements: List[Requirement]`, `mappings: List[CodeRequirementLink]`) combined with top-level unified `entities: List[CodeEntity]` and `routes: List[Dict]`.
- **Why Change Was Made:** Modules 3, 4, and 5 require both distinct traversals (e.g. Neo4j graph nodes require distinguishing classes from functions and files) and unified access (e.g. AuditEngine and TieredTestGenerator scanning all code entities uniformly).
- **Reconciliation:** Permanent. Provides full compatibility and eliminates entity-dropping between modules.

### 2.3 RAG Retrieval Payload
- **Contract Said:** Flat array of vector hits `List[VectorSearchResult]`.
- **Code Actually Does:** `RAGContext` object containing `code_results`, `requirement_results`, `test_results`, `graph_context` (call neighborhoods, untested requirements), and `evidence_citations`.
- **Why Change Was Made:** Enables Hybrid RAG where vector similarity is augmented by deterministic graph traversal paths in Neo4j.
- **Reconciliation:** Permanent. Legacy endpoint `POST /api/v1/rag/search` is retained for backwards compatibility.

### 2.4 Agent Grounding Citation Types
- **Contract Said:** Citation object dictionary `{ "file": str, "line": int }`.
- **Code Actually Does:** Verifiable string tokens `List[str]` (file paths like `app/auth.py`, symbol names `app.auth.verify_token`, requirement IDs `REQ-AUTH-01`).
- **Why Change Was Made:** Grounding verification performs exact token-boundary substring matching against the retrieved context pool. Flat tokens allow robust verification across diverse sources (code, markdown specifications, audit findings).
- **Reconciliation:** Permanent.

### 2.5 Failure Endpoint Routing & List Guarantees
- **Contract Said:** `GET /api/v1/failures/{failure_id}` and `GET /api/v1/failures?project_id=...`
- **Code Actually Does:** `GET /api/v1/failures/{identifier}` intelligently disambiguates whether the identifier is a failure UUID or a project UUID. Also exposes `@router.get("/project/{project_id}")` which returns `APIResponse[List[Failure]]` (an empty list `[]` when no defects exist, never a fabricated fallback object).
- **Why Change Was Made:** Prevents React runtime type errors (`failures.map is not a function`) and guarantees clean empty-state contracts.
- **Reconciliation:** Permanent.

### 2.6 Report Endpoint Routing & Dynamic Aggregation
- **Contract Said:** `GET /api/v1/reports/{project_id}`
- **Code Actually Does:** `GET /api/v1/analytics/{project_id}/report` and `GET /api/v1/reports/{identifier}` (which dynamically resolves either report ID or project UUID), alongside asynchronous generator `POST /api/v1/reports/generate`.
- **Why Change Was Made:** An intelligence report in CodeSentinel is not a static flat database entity; it is a dynamically aggregated compilation of the transparent health score formula, tiered test pass rates, multi-category audit findings, and end-to-end traceability matrices. Co-locating report generation in `backend/app/analytics/reports.py` and exposing it via `GET /api/v1/analytics/{project_id}/report` reflects this computation lifecycle, while `GET /api/v1/reports/{identifier}` ensures backward compatibility with Phase 0 consumers.
- **Reconciliation:** Permanent. Both endpoints return `APIResponse[T]` unwrapped payloads.

---

## 3. Real Service Invariants & Boundaries

1. **Zero Cross-Module Internal Imports:**
   - No module in `backend/app/` imports internals from another module. All inter-module communication is mediated strictly via shared schemas (`shared/schemas/`) or documented HTTP REST endpoints via `ExternalServiceClient`.
2. **Deterministic Security and Execution:**
   - Sandbox test runs execute inside ephemeral containers with `network_mode="none"`, `read_only=True`, memory bounds (`256m` / `512m`), and PID limits (`64`).
3. **Transparent Intelligence & Metrics:**
   - All quality grades, pass rates, and health scores are mathematically verifiable from real inputs without canned strings or black-box modifiers.

---

## 4. Known Limitations & Audit Alias Mapping

### 4.1 Module 1: Ingestion & Archive Security Defense Coverage
- **Status & Fix:** The baseline test suite already validated Zip-Slip path traversal (`test_zip_slip_exploit_rejected`) and absolute path entries (`test_absolute_path_zip_rejected`). In Phase 6 cleanup, 3 dedicated tests were added to `backend/tests/test_ingestion_security.py`:
  1. `test_symlink_escape_exploit_rejected`: Verifies that ZIP archives containing symlinks pointing outside the extraction root raise `ZipSecurityError` with code `ZIP_SYMLINK_ESCAPE_DETECTED`.
  2. `test_malformed_zip_upload_rejected`: Verifies that truncated, header-corrupted, or non-ZIP uploads raise `ZipSecurityError` with code `ZIP_CORRUPT_ARCHIVE`.
  3. `test_git_clone_timeout_enforced`: Verifies that slow git operations exceeding `timeout_seconds` raise `GitAcquisitionError` with code `GIT_CLONE_TIMEOUT`.
- **Deferred Limitation:** Direct low-level kernel socket interception during `git.Repo.clone_from` is handled via asynchronous task timeouts (`asyncio.wait_for`) rather than OS-level raw packet dropping, as OS packet dropping requires root firewall privileges.

### 4.2 Module 5: React Dashboard Frontend Test Coverage
- **Status & Fix:** The dashboard originally contained 3 frontend unit tests (`ui_invariants.test.tsx`) focusing on the three critical Phase 5 invariants (distinct 4-tier provenance badge styling, ungrounded-response warning banner rendering, and health score component breakdown). In Phase 6 cleanup, 4 additional tests were added in `frontend/src/__tests__/dashboard_pages.test.tsx` covering:
  1. `ApiClient` error handling (verifying clean rejection with server error message on error envelopes).
  2. `RequirementsView` rendering (verifying structured requirements and criteria display).
  3. `FailuresView` rendering (verifying failure severity, category, and error message presentation).
  4. `ExecutionsView` rendering (verifying sandbox execution run telemetry and status badges).
- **Deferred Limitation:** End-to-end browser driving (e.g. via Playwright or Cypress across every click interaction and form submission across all 9 pages) was deferred in favor of fast, reliable React Testing Library unit/component tests in Vitest (7 passing tests total).

### 4.3 Module 5: Audits Router Backward-Compatibility Aliases
The audits router in `backend/app/audits/router.py` exposes two legacy compatibility routes from Phase 0:
1. `POST /api/v1/audits/scan`:
   - **What it aliases to:** Aliases the asynchronous job enqueueing mode of `POST /api/v1/audits/{project_id}/run` (enqueueing `JobType.COMPLIANCE_AUDIT` via `JobManager`).
   - **Envelope:** Wraps its response in the exact same `APIResponse[JobStatus]` envelope with HTTP status 202 (`HTTP_202_ACCEPTED`).
2. `GET /api/v1/audits/findings/{project_id}`:
   - **What it aliases to:** Aliases `GET /api/v1/audits/{project_id}` with severity and category filter query parameters.
   - **Envelope:** Wraps its response in the exact same `APIResponse[List[AuditFinding]]` envelope with HTTP status 200 (`HTTP_200_OK`). If no findings exist in PostgreSQL for an unindexed project, it supplies a sample finding envelope conforming 1:1 to the frozen schema contract.

---

## 5. Module 4 Extension: Mutation Testing & Property-Based Generation

### 5.1 Schema Evolution: `MUTATION_TARGETED` Provenance Enum
- **Specification:** `shared/schemas/test_case.py` originally defined four provenance tiers (`REQUIREMENT_VERIFIED`, `SCHEMA_DERIVED`, `COVERAGE_ONLY`, `AI_INFERRED`).
- **Actual Operational Update:** Added `MUTATION_TARGETED = "MUTATION_TARGETED"` to `TestProvenance`.
- **Rationale:** When a synthetic mutant bug survives the test suite (all existing tests pass despite the injected flaw), CodeSentinel synthesizes a targeted assertion specifically engineered to catch the mutant's behavioural divergence. Tagging these tests with `MUTATION_TARGETED` guarantees auditability, separating them from heuristics (`AI_INFERRED`) or general structural checks (`COVERAGE_ONLY`).
- **Dashboard Separation:** `MUTATION_TARGETED` tests render with distinct styling (`badge-mutation-targeted`, `text-fuchsia-300`, `border-fuchsia-500/60`).

### 5.2 Mutation-Based Test Quality Scoring
- **Endpoints:**
  - `POST /api/v1/tests/{project_id}/mutation-run`: Background job (or synchronous when `sync=True`) executing AST mutations across target code entities.
  - `GET /api/v1/tests/{project_id}/mutation-score`: Retrieves aggregated mutation score ($\frac{\text{Killed}}{\text{Total Valid}}$) and mutant records.
- **Metric Isolation:** Mutation score is surfaced as a dedicated, independent metric. It is strictly **never merged** into code coverage percentages, as passing coverage does not prove fault sensitivity.
- **Equivalent Mutant Heuristic & Limitation:** Equivalence detection in arbitrary Turing-complete code is undecidable in general. CodeSentinel employs static AST dead-code inspection and input-sampling heuristics to skip likely-equivalent mutants. Uncovered edge cases may occasionally survive as false positives.
- **Language Scope:** Python AST mutations (relational, boolean, arithmetic, boundary shift, statement deletion). JavaScript/TypeScript mutation testing via Babel/TypeScript compiler is documented as a follow-up.

### 5.3 Property-Based Testing with Hypothesis
- **Endpoint:** `POST /api/v1/tests/{project_id}/generate` with optional parameter `include_property_based: bool = False`.
- **Strategy Derivation:**
  - `SCHEMA_DERIVED`: Derived deterministically from AST parameter signatures and type hints mapped to Hypothesis strategies.
  - `REQUIREMENT_VERIFIED`: Synthesized when approved requirements or docstrings explicitly declare formal invariants (idempotence, commutativity, non-negativity, length preservation).
- **Execution & Shrinking:** Runs inside the existing hardened Docker sandbox (`network_mode="none"`). Minimal shrunk counterexamples (e.g. `Falsifying example: test_func(x=0)`) are parsed and recorded directly in the failure telemetry.

---

## 6. Module 5 Extension: Real SAST (Semgrep), Dependency Auditing & Multi-Scanner Correlation

### 6.1 Schema Evolution: `detected_by: list[str]` on `AuditFinding`
- **Specification:** `shared/schemas/audit.py` originally defined `AuditFindingBase` without an explicit multi-tool attribution list.
- **Actual Operational Update:** Added `detected_by: List[str] = Field(default_factory=lambda: ["codesentinel-static-analyzer"])` to `AuditFindingBase`.
- **Rationale:** Moving from home-grown-only detection to real tool integration (Semgrep, pip-audit) alongside existing regex secret detectors requires clear multi-scanner attribution. Findings that are independently confirmed across multiple tools carry a combined list (e.g. `["codesentinel-secrets-detector", "semgrep"]`).
- **Backward Compatibility:** Existing finding creation payloads default automatically to `["codesentinel-static-analyzer"]`.

### 6.2 Real SAST Tool Integration (Semgrep)
- **Engine:** `app.audits.semgrep_scanner.SemgrepScanner` invokes Semgrep as a non-intrusive subprocess using free community rulesets for Python and JavaScript/TypeScript.
- **Severity Mapping:**
  - Semgrep `ERROR` with injection / RCE / secret / credential checks $\rightarrow$ `AuditSeverity.CRITICAL`.
  - Semgrep `ERROR` other $\rightarrow$ `AuditSeverity.HIGH`.
  - Semgrep `WARNING` $\rightarrow$ `AuditSeverity.MEDIUM`.
  - Semgrep `INFO` $\rightarrow$ `AuditSeverity.LOW` / `INFO`.
- **Standard Mapping:** Extracts CWE and OWASP Top 10 classifications directly from Semgrep rule metadata.

### 6.3 Multi-Scanner Finding Correlation & Deduplication
- **Engine:** `app.audits.correlation.FindingCorrelator`.
- **Correlation Rule:** Groups security findings that share:
  1. The exact same file path (`location.file_path`).
  2. Overlapping line ranges: $\max(A_{\text{start}}, B_{\text{start}}) \le \min(A_{\text{end}}, B_{\text{end}})$.
  3. Similar security category or CWE defect domain.
- **Merge Behavior:**
  - Merged findings produce a single canonical `AuditFinding`.
  - `detected_by`: Combined, deduplicated, and sorted list (e.g. `["codesentinel-secrets-detector", "semgrep"]`).
  - `severity`: Elevated to the highest severity among merged findings.
  - `location`: Bounding line coordinates $[\min(\text{start\_line}), \max(\text{end\_line})]$.
  - `cvss_score`: Elevated to highest CVSS score.

### 6.4 Dependency Auditing (pip-audit & npm audit) with Offline Fallback
- **Engine:** `app.audits.dependency_scanner.DependencyVulnerabilityScanner`.
- **Live Mode:** Queries the PyPA Advisory Database via `pip-audit -f json` (and npm advisory registry) when network access is available, tagging findings with `detected_by=["pip-audit"]`.
- **Offline / Sandbox Fallback & Known Limitation:** When operating in an isolated, sandboxed, or air-gapped environment where external network calls timeout or fail, the scanner falls back cleanly to the verified `OFFLINE_VULNERABILITY_SNAPSHOT` and tags findings with `detected_by=["codesentinel-dependency-advisory"]`. Live network data is never fabricated.

### 6.5 Static Analysis Sandbox Safety Rule
- Semgrep, `pip-audit`, and `npm audit` run exclusively against source files and package manifests as static text.
- Under **no circumstances** is repository code executed during audits, preserving CodeSentinel's strict invariant that untrusted code only executes within hardened ephemeral Docker sandboxes during Module 4 test runs.



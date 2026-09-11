# CodeSentinel: AI-Powered Autonomous Software Engineering Intelligence Platform

CodeSentinel is an end-to-end, production-grade autonomous software engineering intelligence platform. It performs deep structural AST parsing, knowledge graph relationship mapping, semantic code retrieval (RAG), requirement-verified test generation, and executes test suites inside isolated Docker execution sandboxes with automated root cause diagnosis (RCA).

---

## 1. Architectural Highlights & Invariants

- **Zero Cross-Module Internal Imports:** All 5 core engineering modules communicate strictly through documented REST endpoints and the frozen schema layer (`shared/schemas/`).
- **Standard Envelope:** 100% of endpoints return responses structured within the `APIResponse[T]` envelope.
- **Strict Provenance Enforcement:** `TestCase` models are bound to immutable provenance tiers:
  - `REQUIREMENT_VERIFIED` (Strictly linked to explicit requirement acceptance criteria; zero generated for requirements without criteria)
  - `SCHEMA_DERIVED` (Synthesized from API contracts and data models)
  - `COVERAGE_ONLY` (Targeting uncovered branches and AST statements)
  - `AI_INFERRED` (Heuristically deduced boundary and edge conditions)
- **Hardened Docker Sandbox:** Ephemeral test containers enforce `network_mode="none"`, `read_only=True`, memory/CPU bounds, non-root user execution, and strict timeouts.
- **Evidence-Grounded AI Assistant:** Responses must cite candidate tokens verified against real RAG/graph context or are flagged `is_grounded=False`.
- **Transparent Health Score:** Health scores are computed deterministically without black-box modifiers:
  $$\text{Health Score} = 0.35 \times \text{ReqCoverage} + 0.25 \times \text{ReqPassRate} + 0.15 \times \text{Quality} + 0.15 \times \text{Security} + 0.10 \times \text{Architecture}$$
- **Zero Unified Coverage Fabrication:** Coverage is reported strictly per-language ecosystem without cross-language fabrication.

---

## 2. Monorepo Layout

```
CodeSentinel/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Aggregated route endpoints
│   │   ├── core/            # Database (SQLAlchemy), Redis, Envelope, Config
│   │   ├── models/          # PostgreSQL SQLAlchemy ORM models
│   │   ├── ingestion/       # Module 1: Repo cloning, validation, and zip parsing
│   │   ├── profiler/        # Module 1: Language/framework profiling
│   │   ├── analyzer/        # Module 2: AST Tree-sitter & System Model
│   │   ├── requirements/    # Module 2: Strict criteria extractor & traceability
│   │   ├── knowledge_graph/ # Module 3: Neo4j graph materializer & queries
│   │   ├── rag/             # Module 3: Qdrant dense vector indexer & search
│   │   ├── agents/          # Module 3: Grounded multi-agent reasoning
│   │   ├── testing/         # Module 4: Tiered test case synthesis
│   │   ├── sandbox/         # Module 4: Hardened Docker sandbox executor
│   │   ├── failures/        # Module 4: Failure triage & Root Cause Analysis (RCA)
│   │   ├── audits/          # Module 5: Deterministic Code/Security/Coverage/Arch audits
│   │   └── analytics/       # Module 5: Health score engine, matrix, and reports
│   ├── tests/               # 121 passing PyTest tests including E2E integration
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # UI components, badges, layouts
│   │   ├── pages/           # Real-wired views (Overview, Tests, Failures, Audits, Analytics, AI)
│   │   ├── services/        # Live ApiClient unwrapping APIResponse<T>
│   │   └── types/           # TypeScript schemas
│   ├── package.json
│   └── vite.config.ts
├── shared/
│   └── schemas/             # Frozen Pydantic schemas (Single Source of Truth)
├── sample_project/          # Real sample microservice for end-to-end demo verification
├── CONTRACTS.md             # Theoretical contract specifications
├── CONTRACTS_ACTUAL.md      # Operational contracts & verified divergences
└── docker-compose.yml       # postgres, redis, neo4j, qdrant backing services
```

---

## 3. Verified Prerequisites

- **Python:** 3.11 or 3.12 (Virtual environment recommended)
- **Node.js:** 18.x or 20.x (`npm`)
- **Docker:** Docker Desktop or Docker Engine running with Docker Compose v2+
- **Operating System:** Windows, Linux, or macOS

---

## 4. Quickstart Setup Instructions

### Step 1: Clone and Configure Environment
```bash
git clone https://github.com/your-org/CodeSentinel.git
cd CodeSentinel

# Copy environment variables template
cp .env.example .env
```

### Step 2: Start Backing Services (Docker Compose)
Start the PostgreSQL, Redis, Neo4j, and Qdrant containers:
```bash
docker compose up -d postgres redis neo4j qdrant
```

Verify backing containers are healthy:
- **PostgreSQL:** `localhost:5432` (`codesentinel` / `codesentinel_secret`, DB: `codesentinel_db`)
- **Redis:** `localhost:6379`
- **Neo4j:** `localhost:7687` (`neo4j` / `codesentinel_graph_secret`)
- **Qdrant:** `http://localhost:6333`

### Step 3: Setup Backend Python Environment
```bash
# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### Step 4: Setup Frontend Environment
```bash
cd frontend
npm install
cd ..
```

---

## 5. Running the Application

### Start the Backend Server:
```bash
# From workspace root with .venv active:
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
- API Documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- OpenAPI JSON Spec: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### Start the Frontend Dev Server:
```bash
cd frontend
npm run dev
```
- Dashboard UI: [http://localhost:5173](http://localhost:5173)

---

## 6. Running the Test Suites

### Backend Tests (124 Passing Tests):
```bash
# From workspace root:
pytest backend/tests/ -v
```

To run the automated 10-step End-to-End System Integration test:
```bash
pytest backend/tests/test_e2e_integration.py -v -s
```

### Frontend Tests (7 Passing Tests + Clean Build):
```bash
cd frontend
npx vitest run
npm run build
```

---

## 7. Verifying the Real Sample Project

The repository includes a purpose-built sample microservice in `sample_project/` containing:
- `requirements.md`: `REQ-AUTH-01` (explicit acceptance criteria) and `REQ-CACHE-02` (vague prose with no criteria).
- `app/main.py`: FastAPI endpoints.
- `app/auth.py`: Token verification, high-complexity policy function, and a planted credential (`AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE"`).
- `app/calculator.py`: Arithmetic utility.
- `tests/`: Real unit tests including a deliberate boundary assertion failure (`1 == 2`).

### 10-Step Journey Verification Results:
1. **Profiling:** Accurately profiles Python/FastAPI codebase.
2. **Analysis:** Assembles system model; extracts `REQ-AUTH-01` with criteria and leaves `REQ-CACHE-02` with 0 criteria.
3. **Knowledge Graph & RAG:** Materializes graph nodes in Neo4j; indexes AST chunks in Qdrant.
4. **AI Assistant:** Grounding engine confirms answer cites real code tokens from `app/auth.py`.
5. **Tiered Test Generation:** Generates `REQUIREMENT_VERIFIED` tests for `REQ-AUTH-01`; generates ZERO for `REQ-CACHE-02`.
6. **Sandbox Execution:** Executes in hardened container; classifies PASS / FAIL results.
7. **Failure Diagnosis:** Triages deliberate failure (`assert 1 == 2`); correlates root cause without fabrication.
8. **Multi-Category Audits:** Real audit catches planted AWS key and flags cyclomatic complexity.
9. **Dashboard & Analytics:** Transparent health score and full requirement-to-execution traceability matrix.
10. **Assurance Reports:** Generates executive Markdown and structured JSON assurance reports.

---

## 8. Operational Limitations & Known Limitations

- **Database Persistence & Migrations:** 100% real PostgreSQL 16 relational storage via SQLAlchemy async sessions.
- **Graph & Vector Stores:** 100% real Neo4j 5.x graph traversals and real Qdrant vector indexing/search.
- **Docker Sandbox Execution:** 100% real ephemeral Docker container orchestration enforcing network isolation, read-only rootfs, and memory limits.
- **Multi-Category Audits:** 100% deterministic AST visitors and regex rules (cyclomatic complexity, high-entropy secrets, outdated dependencies, circular imports).
- **LLM Reasoning & Agent Personas:** When commercial LLM API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are present in `.env`, agents invoke live frontier models. In local air-gapped environments without API keys, agents automatically fallback to deterministic rule-based semantic extractors and grounding verifiers, ensuring reliable operation in any environment.

### Explicit Known Limitations & Scope Boundaries:
1. **Module 1 (Ingestion Security Tests):** Zip-Slip path-traversal, symlink-escape exploits (`ZIP_SYMLINK_ESCAPE_DETECTED`), corrupt/malformed archive uploads (`ZIP_CORRUPT_ARCHIVE`), and git-clone timeouts (`GIT_CLONE_TIMEOUT`) are verified by 9 unit tests. Raw OS-level packet dropping during git clone operations was deferred to container network isolation as host packet dropping requires root firewall privileges.
2. **Module 5 (Frontend Dashboard Testing):** 7 tests verify core invariants (provenance badge styling, ungrounded response warning banner, health score breakdown display, API client error rejection, and individual page rendering). End-to-end browser automation (Playwright/Cypress) across every user form submission was deferred in favor of lightweight, fast Vitest component tests.
3. **Module 5 (Audits Aliases):** `/api/v1/audits/scan` and `/api/v1/audits/findings/{project_id}` serve as backward-compatibility aliases to `POST /api/v1/audits/{project_id}/run` (async mode) and `GET /api/v1/audits/{project_id}`, respectively, each returning through the identical `APIResponse[T]` envelope.

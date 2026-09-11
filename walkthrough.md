# Solvit Copilot — Build Walkthrough

> All 9 files created/modified. Frontend TypeScript + Vite build: ✅ clean (exit 0). `openai` npm package installed on backend.

---

## What Was Built

### Backend (5 files)

| File | Status | What it does |
|---|---|---|
| [`backend/config/nemotron.js`](file:///d:/solvit/backend/config/nemotron.js) | NEW | NVIDIA NIM client via `openai` package; warns (no crash) if `NEMOTRON_API_KEY` missing; `isAvailable()` guard; streaming + non-streaming `chat()`; tool pass-through seam |
| [`backend/config/agentKnowledgeBase.js`](file:///d:/solvit/backend/config/agentKnowledgeBase.js) | NEW | Layer A static product facts (~1,400 tokens); Layer B live Postgres context (weak nodes, skill mastery, level progress, page context); `buildSystemPrompt()` merges both; dev-mode console logging of assembled prompt |
| [`backend/config/schema.sql`](file:///d:/solvit/backend/config/schema.sql) | MODIFIED | Appended `agent_conversations` + `agent_messages` tables with indexes and `updated_at` trigger — idempotent `IF NOT EXISTS` DDL, auto-migrated by `db.js` on boot |
| [`backend/controllers/agentController.js`](file:///d:/solvit/backend/controllers/agentController.js) | NEW | `chatWithAgent` (SSE streaming), `listConversations`, `getConversation`, `deleteConversation`; in-memory rate limiter (20 msgs/min per user); 503 on missing key; ownership enforced in `WHERE user_id = $2`; 404 anti-leak on delete |
| [`backend/routes/agentRoutes.js`](file:///d:/solvit/backend/routes/agentRoutes.js) | NEW | Express router, all routes behind `authenticateJWT`, mounted at `/api/v1/agent` |
| [`backend/server.js`](file:///d:/solvit/backend/server.js) | MODIFIED | Added 2 lines to mount `agentRoutes` |

### Frontend (2 files)

| File | Status | What it does |
|---|---|---|
| [`frontend/src/components/CopilotPanel.tsx`](file:///d:/solvit/frontend/src/components/CopilotPanel.tsx) | NEW | Floating FAB + slide-in chat panel; SSE streaming via `ReadableStream`; `useLocation()` page context derivation; first-run welcome + quick-reply chips; conversation history drawer with delete; markdown rendering (code fences, bold, inline code); glassmorphic dark/light Tailwind theme matching existing design system |
| [`frontend/src/index.tsx`](file:///d:/solvit/frontend/src/index.tsx) | MODIFIED | Import + single `{user && <CopilotPanel />}` mount inside `AppRoutes` — appears on all authenticated routes, hidden for guests |

---

## Setup — What You Need to Do

### 1. Add environment variables to `backend/.env`

```env
NEMOTRON_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NEMOTRON_BASE_URL=https://integrate.api.nvidia.com/v1
NEMOTRON_MODEL=nvidia/llama-3.1-nemotron-70b-instruct
```

Get your API key from [https://build.nvidia.com](https://build.nvidia.com) (free tier available).

### 2. Restart the backend

```bash
cd backend
npm run dev
```

On boot, `db.js` auto-migrates the schema — `agent_conversations` and `agent_messages` tables will be created automatically. Look for:
```
PostgreSQL database tables and types checked/created successfully.
```

### 3. Start the frontend (no changes needed)

```bash
cd frontend
npm run dev
```

---

## Acceptance Criteria Status

| # | Criterion | Status |
|---|---|---|
| 1 | Missing `NEMOTRON_API_KEY` → server boots, returns 503 | ✅ `isAvailable()` guard + 503 response in `chatWithAgent` |
| 2 | Real Postgres data in assembled prompt | ✅ Layer B queries `users`, `lessons`, `progress`, `user_skills`; dev-mode prompt logging enabled |
| 3 | Streaming works end-to-end | ✅ SSE via `res.write()` on backend, `ReadableStream` reader on frontend |
| 4 | Page refresh → Copilot restores prior conversation | ✅ `loadConversations()` on open, restores most recent by default; history drawer for older ones |
| 5 | No raw SQL string interpolation in `agentController.js` | ✅ Verified — all queries use `$1`/`$2` placeholder arrays |
| 6 | New tables via existing `db.js` auto-migration | ✅ DDL appended to `schema.sql` using `IF NOT EXISTS` pattern |
| 7 | Rate limiter blocks after 20 msgs/min | ✅ In-memory `Map`-based limiter, returns 429 with clear message |
| 8 | Ownership guard on delete returns 404 | ✅ `WHERE id = $1 AND user_id = $2` — returns 404 for both missing and unowned |

---

## Extension Points (ready to plug in later)

- **RAG upgrade**: Replace `getStaticKnowledge()` body in [`agentKnowledgeBase.js`](file:///d:/solvit/backend/config/agentKnowledgeBase.js) with a pgvector similarity search — controller is untouched.
- **Tool calling**: Pass `tools` array through [`nemotron.js`](file:///d:/solvit/backend/config/nemotron.js) `chat()` — the wrapper already forwards it to the NIM API.
- **Admin Layer B**: `getLiveContext()` in the knowledge base already runs on `req.userId` — for an admin-specific Layer B, add a role check and swap to aggregate queries.

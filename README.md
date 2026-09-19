# AI Finance Assistant — multi-agent backend

![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688)
![Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-4285F4)
![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)

A FastAPI backend for a Vietnamese-market finance assistant built as an **orchestrator + critic
agent loop**: the orchestrator plans which tools to call, a critic reviews both the plan and the
tool results, and the loop iterates until the critic is satisfied or the budget is spent. Tools
cover live Vietnamese stock data (via `vnstock`), web search (Tavily) and RAG over the user's own
financial documents (Gemini embeddings + Qdrant). Progress is streamed to the client as
Server-Sent Events so the UI can show *planning → reviewing → executing → answering* live.

The Next.js frontend lives in a separate repository; this repo is the API.

---

## Table of contents

- [How the agent loop works](#how-the-agent-loop-works)
- [Tools](#tools)
- [HTTP API](#http-api)
- [Streaming protocol](#streaming-protocol)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Project layout](#project-layout)
- [Design notes and known issues](#design-notes-and-known-issues)

---

## How the agent loop works

```text
user query
   │
   ▼
AgentLoop (src/agents/agent_loop.py)
   ├─ 1. Orchestrator.classify_query()        SIMPLE  → one tool, no critic, answer directly
   │                                           COMPLEX → full loop below
   ├─ 2. Orchestrator.create_plan()           LLM produces an OrchestratorPlan: ordered ToolPlan[]
   ├─ 3. Critic.review_plan()                 approve / require changes / ask the user to clarify
   ├─ 4. Orchestrator.execute_tools()         tools run (in parallel when independent)
   ├─ 5. Critic.review_results()              score 0–5, concerns, suggestions, iteration feedback
   │        └─ not approved and iterations left → back to 2 with the critic's feedback
   └─ 6. Orchestrator synthesises the final answer from accumulated ToolResult[]
```

- **Orchestrator** (`orchestrator.py`) — understands the request, writes a typed plan
  (`OrchestratorPlan` → `ToolPlan[]`), executes tools, synthesises the answer. Simple lookups such
  as *"giá cổ phiếu VCB"* are matched by regex and short-circuited to a single `vnstock` call.
- **Critic** (`critic.py`) — a reflection layer with a structured verdict (`CriticReview`:
  `approved`, `score`, `concerns`, `suggestions`, `requires_changes`, `needs_clarification`,
  `clarification_questions`). Low scores send feedback back to the orchestrator; mid scores can
  turn into clarifying questions for the user instead of guessing.
- **AgentLoop** — owns the budget (`max_iterations`, default 3; `timeout_seconds`, default 60),
  parallel tool execution, per-stage progress callbacks and the metrics returned with every run.
- **StateManager** (`state/manager.py`) — per-session agent state and scratch memory, persisted
  in Supabase so a run can be inspected or resumed.
- **FinanceAgent** (`finance_agent.py`) — a Gemini function-calling agent for personal-finance
  questions (balances, spending trends, document RAG) used by the plain chat endpoint.

Every plan, review and tool result is a Pydantic model, so the whole trace is serialisable and is
what the streaming endpoint sends to the UI.

## Tools

| Tool | Used by | Source | What it returns |
| --- | --- | --- | --- |
| `vnstock_get_quote` | Orchestrator | `tools/vnstock_tool.py` | Current price, change, volume for a HOSE/HNX/UPCOM symbol (`vnstock` v3, lazy-loaded, run in an executor thread). |
| `vnstock_get_company_info` | Orchestrator | `tools/vnstock_tool.py` | Company profile and fundamentals. |
| `tavily_web_search` | Orchestrator | `tools/tavily_search.py` | Web results for news and context, async via `aiohttp`. |
| `search_finance_knowledge` | FinanceAgent | `skills/rag_skill.py` → `services/rag_service.py` | Top-k chunks from the user's uploaded financial PDFs (RecursiveCharacterTextSplitter 1500/200, Gemini embeddings, Qdrant). |
| `get_user_balance`, `analyze_spending_trends` | FinanceAgent | `finance_agent.py` | Personal-finance lookups over the user's Supabase data. |

`GET /api/v1/agent/tools` lists the tools the orchestrator can currently plan with.

## HTTP API

| Area | Endpoints |
| --- | --- |
| Agent | `POST /api/v1/agent/query` (sync, returns the full trace), `POST /api/v1/agent/query/stream` (SSE), `GET /api/v1/agent/tools`, `POST /api/v1/agent/test/orchestrator`, `POST /api/v1/agent/test/critic` |
| Mock agent | `/api/v1/mock/agent/*` — same shapes with canned data and forced-error variants, so a frontend can be built without spending model quota |
| Conversations | `POST /api/v1/conversations` (list), `/create`, `GET/PUT/DELETE /{id}`, `/{id}/rename`, `/{id}/generate-title`, `/{id}/action`, `/{id}/export`, folders (`/folders`, `/folders/create`, `PUT/DELETE /folders/{id}`), `/bulk/move`, `/bulk/delete`, `/stats/summary` |
| Chat | `POST /api/chat` — streaming chat with the `FinanceAgent` (falls back to a mock stream without an API key) |
| Health | `GET /`, `GET /health` |

The same routers are also mounted under `/api` (without `v1`) for backward compatibility. Request
and response schemas are in `src/api/schemas/` and described in
[`docs/openapi/agent-api.v1.yaml`](docs/openapi/agent-api.v1.yaml).

## Streaming protocol

`POST /api/v1/agent/query/stream` returns `text/event-stream`. The loop reports progress through a
callback; the route turns each report into one `data:` line with an `event_type` and a typed
payload:

`START` → `PLANNING` → `PLAN_CREATED` → `CRITIC_REVIEWED` → `TOOL_EXECUTING` / `TOOL_COMPLETED`
(per tool) → `SYNTHESIZING` → `FINAL_RESULT`, or `TIMEOUT` / `AGENT_ERROR` / `ERROR`.

`FINAL_RESULT` carries the answer plus metrics (iterations, execution time, critic score, tool
calls). `docs/fe_be_schema_mapping.md` maps these events to the frontend's message model.

## Quick start

Python **3.11** (pinned in `runtime.txt`; the pinned `numpy`/`pandas` versions have no 3.12
wheels).

```powershell
git clone https://github.com/ducduong12123/AI_finance.git
cd AI_finance
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env        # set GOOGLE_API_KEY at minimum; TAVILY/SUPABASE/QDRANT as needed
python run.py                      # http://127.0.0.1:8001  (Swagger UI at /docs)
```

Without any keys the mock router still answers, e.g.

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/v1/mock/agent/query `
  -ContentType 'application/json' -Body '{"query":"Giá VCB","maxIterations":3}'
```

`docker-compose.yml` / `Dockerfile` are a draft of a combined backend + frontend + Redis stack
and still use the older `GEMINI_API_KEY` name; for now run with `run.py` or deploy to Railway.

## Configuration

Loaded by `src/core/config.py` (pydantic-settings) from the environment or a `.env` in the repo
root.

| Variable | Default | Used by |
| --- | --- | --- |
| `GOOGLE_API_KEY` | — | Gemini chat, orchestrator, critic, embeddings |
| `PRIMARY_MODEL` / `EMBEDDING_MODEL` | `gemini-3-flash-preview` / `gemini-embedding-001` | model names, single source of truth |
| `TAVILY_API_KEY` | — | `tavily_web_search` |
| `SUPABASE_URL` / `SUPABASE_KEY` | — | conversations, folders, agent state |
| `QDRANT_HOST` / `QDRANT_PORT` / `QDRANT_API_KEY` | `localhost` / `6333` / — | document RAG |

## Deployment

Railway-ready: `railway.json` (Nixpacks, health check on `/health`), `nixpacks.toml`
(Python 3.11 + gcc), `Procfile`. The deploy guide is in
[`DEPLOY_RAILWAY.md`](DEPLOY_RAILWAY.md); database bootstrap in
[`docs/DATABASE_SETUP.md`](docs/DATABASE_SETUP.md).

## Project layout

```text
src/
  main.py                 FastAPI app, CORS, routers, /api/chat streaming endpoint
  core/config.py          settings
  agents/
    agent_loop.py         loop controller: budget, parallel execution, progress callbacks, metrics
    orchestrator.py       planning, tool execution, synthesis, SIMPLE/COMPLEX classification
    critic.py             plan + result review with a structured verdict
    finance_agent.py      Gemini function-calling agent for personal finance
    base.py               shared Gemini agent base
    tools/                vnstock_tool.py, tavily_search.py
    skills/rag_skill.py   document RAG as a tool
    state/manager.py      per-session state in Supabase
  api/routes/             agent.py (real), agent_mock.py (canned), conversations.py
  api/schemas/            Pydantic request/response models
  services/               chat_service.py (streaming), rag_service.py (PDF → Qdrant), agent_db_service.py
  data/adapters/          qdrant_client.py, supabase_client.py
docs/                     system_spec.md (source of truth, Vietnamese), OpenAPI, FE↔BE schema mapping,
                          database setup, API guidelines
plans/                    agent_architecture_overview.md (Mermaid diagrams of the loop)
scripts/manual/           hand-run checks for the tools and the chat endpoint
```

## Design notes and known issues

- **Why a critic?** For analysis questions ("compare VCB and TCB this quarter") a single planning
  pass tends to under-fetch; the critic's structured review turns that into a bounded retry with
  explicit feedback instead of an open-ended loop.
- **Why short-circuit simple queries?** [`AGENT_LOOP_OPTIMIZATION.md`](AGENT_LOOP_OPTIMIZATION.md)
  documents the measured problem: a price lookup used to run 3 iterations and 6–9 model calls
  (10–15 s). Regex classification now sends it straight to one `vnstock` call.
- Open item from the same document: tool results are not yet carried across iterations, so a
  retried plan re-fetches; accumulating `ToolResult[]` is the next optimisation.
- Prompts and most docs are in Vietnamese, matching the target users.
- The project was developed with a split of work between AI coding agents (backend / frontend /
  integration); `docs/AGENT_3_INTEGRATION_GUIDE.md` and `docs/agent_brain_log.md` are that
  process's artefacts, kept for transparency.
- Dependencies are pinned to early-2026 versions of `langchain` 0.1 and `google-generativeai`
  0.3; upgrading to `langchain-core` ≥ 0.3 and `google-genai` is the next maintenance task.

## License

MIT — see [LICENSE](LICENSE).

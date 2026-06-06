# CLAUDE.md — Lex Companion Agent Instructions

This file guides AI coding agents working in the **Lex Companion** repository.

---

## Project Overview

**Lex Companion** is an agentic Vietnamese Legal AI Assistant. It helps individuals and businesses understand Vietnamese regulations, research legal issues, evaluate options, and generate legal documents through specialized LangGraph agents grounded in authoritative legal sources.

**Main product goal:** Deliver grounded, traceable legal assistance over the Vietnamese **Pháp điển** legal codex (~64k articles) — not generic chatbot answers.

**Main capabilities:**
- Intent-specific LangGraph agent workflows (6 intents)
- Hybrid Elasticsearch RAG (keyword + semantic + BGE reranking)
- Citation-backed responses with inline `[n]` references and IEEE-style reference panel
- Human-in-the-loop (HITL) contract/document generation (DOCX)
- Session-scoped user document upload and retrieval
- Web fallback via Tavily when corpus context is insufficient

**Target users:**
- Legal professionals — research, citation-backed answers, document drafting
- Citizens / SMEs — legal Q&A, decision guidance, contract template filling
- Administrators — corpus ingestion, Elasticsearch indexing, retrieval tuning

---

## Architecture Summary

| Layer | Technology | Location |
|-------|------------|----------|
| **Frontend** | Next.js 16, React 19, TanStack Query, Tailwind CSS 4 | `web/` |
| **Backend API** | FastAPI, Uvicorn, Peewee ORM, Pydantic v2 | `api/` |
| **Agent workflows** | LangGraph `StateGraph`, intent routing | `deepagent/multiagent/legal_assistant/` |
| **RAG / search** | Elasticsearch 8.13 hybrid search, BGE reranker | `api/apps/services/retrieval/`, `api/utils/elastic_chunk_index.py` |
| **Database / storage** | PostgreSQL (Peewee), MinIO (files), Redis (task queue) | `api/db/`, `api/utils/` |
| **Background workers** | Redis Streams consumer for parsing/indexing | `api/worker/` |
| **Document generation** | LangGraph task_execution + python-docx + MinIO | `deepagent/multiagent/legal_assistant/task_execution/` |
| **Embedding service** | Vietnamese_Embedding_v2 (OpenAI-compatible) | `model_serving/embeddings/vie_embedding_v2/` |

**Request flow (Inferred from implementation):**

```
User message → JWT auth → understand_user_true_intent() → intent routing
→ LangGraph agent → hybrid retrieval → rerank → LLM with citations → persist & respond
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/AGENTS.md](docs/AGENTS.md) for detailed diagrams.

---

## Development Commands

All commands below are taken from the repository. Run from the **repository root** unless noted.

### Backend dependencies

```bash
uv venv --python 3.12
uv sync                  # Production dependencies
uv sync --group dev      # Include langgraph-cli
```

> **Do not** run `uv pip install -e .` — this project uses `package = false` in `pyproject.toml` and runs via `PYTHONPATH=.`.

### Run the backend

```bash
uv run --env-file .env python -m api.lex_companion_server
# API at http://localhost:5999
# OpenAPI docs at http://localhost:5999/docs
```

Or via script:

```bash
./scripts/start_lex_api.sh
```

> **Do not** run `python api/lex_companion_server.py` directly. Always use `python -m api.lex_companion_server` with `PYTHONPATH=.`.

### Run the frontend

```bash
cd web
npm install
npm run dev    # http://localhost:3004
npm run build
npm run start
npm run lint
```

### Docker (full stack)

```bash
# Linux: if Elasticsearch fails to start
sudo sysctl -w vm.max_map_count=262144

docker compose -f docker/docker-compose.yml up -d --build
```

| Service | Host URL |
|---------|----------|
| Web UI | http://localhost:3005 |
| API | http://localhost:6000 |
| API Docs | http://localhost:6000/docs |
| Kibana | http://localhost:5602 |

### Tests

```bash
uv run python -m pytest tests/
```

### LangGraph dev tools

```bash
uv sync --group dev
uv run langgraph dev
```

> **Warning:** `langgraph.json` references a legacy path `legal_agent.agent:graph`. Active graphs live in `deepagent/multiagent/legal_assistant/`. Do not point new work at the legacy path.

### Embedding service (optional, self-hosted)

```bash
cd model_serving/embeddings/vie_embedding_v2
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py   # port 6501
```

### Add Python dependencies

```bash
uv add <package>           # Production
uv add --dev <package>     # Dev
uv sync
```

---

## Repository Structure

```
langgraph-base/
├── api/                         # FastAPI backend
│   ├── lex_companion_server.py  # Entry point; auto-loads routers
│   ├── apps/
│   │   ├── routers/             # Route definitions (auto-discovered)
│   │   ├── controllers/         # Request handlers (try/except, envelope)
│   │   └── services/            # Business logic, orchestration, retrieval
│   ├── db/models.py             # Peewee ORM models
│   └── worker/                  # Redis Streams background worker
├── deepagent/                   # LangGraph agents + core AI utilities
│   ├── multiagent/legal_assistant/  # Intent-specific graphs
│   └── core/                    # Rerank, splitters, HITL, query rewriting
├── web/                         # Next.js frontend
├── model_serving/               # Standalone embedding + optional LLM proxy
├── docker/                      # Docker Compose + Dockerfiles
├── docs/                        # Technical documentation
├── scripts/                     # Startup scripts (start_lex_api.sh)
├── pyproject.toml               # Python deps (uv)
└── .env.example                 # Environment template
```

### Important folders

| Folder | Purpose |
|--------|---------|
| `api/` | REST API, orchestration, retrieval service, DB models, workers |
| `deepagent/` | LangGraph agent graphs, shared state, tools, HITL, reranking |
| `web/` | Next.js UI — chat, citations, HITL form fill, admin visualization |
| `model_serving/` | Self-hosted embedding API; optional Ollama/Phi3 LLM proxy |
| `docker/` | Full-stack Docker Compose (Postgres, MinIO, Redis, ES, API, Web) |
| `docs/` | Architecture docs; agent system docs in `docs/AGENTS.md` |
| `scripts/` | Shell helpers for local API startup |

---

## Coding Conventions

### Python

- **Version:** Python 3.12+ (`requires-python = ">=3.12"` in `pyproject.toml`)
- **Package manager:** [uv](https://docs.astral.sh/uv/) — not pip for project deps
- **ORM:** Peewee — **not** SQLAlchemy
- **Validation:** Pydantic v2 for request/response schemas in orchestration layer
- **Type hints:** Use throughout; agent state is `LegalAssistantState` TypedDict

### API layering

Follow the pattern documented in `api_creating_instruction.md`:

```
Router → Controller → Service → DB / ES / MinIO / Agent Registry
```

Rules:
- Controllers wrap logic in `try/except`; never let routers handle exceptions
- Controllers do not access DB directly — delegate to services
- Prefer `common_service.py` helpers for simple CRUD
- JWT-protected routes go through `api/apps/middleware/jwt_auth.py` first

### Response envelope

All API responses use:

```json
{ "code": 200, "msg": "OK", "data": { ... } }
```

HTTP status codes follow REST conventions (200 success, 201 created, 400/401/403/404/502 as appropriate).

### Environment variables

- Copy `.env.example` → `.env` at repo root
- Never commit secrets (API keys, JWT secret, DB passwords)
- Load via `uv run --env-file .env` or Docker `env_file`
- Frontend build-time vars: `web/.env` with `NEXT_PUBLIC_*` prefix

### Frontend conventions

- **Framework:** Next.js 16 Pages Router, React 19
- **Data fetching:** TanStack Query hooks in `web/hooks/`; API clients in `web/service/`
- **Endpoints:** Mapped in `web/apis/endpoints.ts` via `NEXT_PUBLIC_API_SERVER`
- **i18n:** Vietnamese and English via `web/locale/`

### Where to add new code

| Change | Location |
|--------|----------|
| New API endpoint | `api/apps/routers/` → `controllers/` → `services/` |
| New agent intent | `deepagent/multiagent/legal_assistant/<intent>/` + register in `registry.py` |
| New retrieval logic | `api/apps/services/retrieval/` |
| New graph node | Intent folder's `nodes.py` + wire in `graph.py` |
| Frontend feature | `web/views/`, `web/hooks/`, `web/service/` |

---

## Agent Development Rules

### Where LangGraph agents live

```
deepagent/multiagent/legal_assistant/
├── registry.py              # Graph cache + invoke helpers
├── shared/state.py          # LegalAssistantState TypedDict
├── shared/checkpointer.py   # InMemorySaver (task_execution only)
├── information/             # Full RAG workflow (primary)
├── decision/                # Partial — single-node
├── problem_solving/         # Partial — single-node
├── exploration/             # Partial — single-node
├── communication_normal/    # Social chat (no RAG)
├── task_execution/          # HITL contract fill (checkpointer)
└── tools/                   # Direct-invoke tools (not ReAct)
```

### Agent state management

- Shared state: `LegalAssistantState` in `shared/state.py`
- State is a plain `TypedDict` passed through LangGraph nodes
- Each node returns an updated dict; LangGraph merges into state
- Orchestrator builds initial state in `api/apps/services/orchestration/chat_orchestrator.py`
- Reranker instance is injected from `request.app.state.reranker` at API layer

### How to add a new node

1. Implement node function in `<intent>/nodes.py` — signature: `(state: LegalAssistantState) -> LegalAssistantState`
2. Register node in `<intent>/graph.py` via `builder.add_node(...)`
3. Wire edges or conditional edges
4. Do not mutate shared caches or global singletons inside nodes
5. Return a new dict copy (`next_state = dict(state)`) rather than in-place mutation when possible

### How to add a new intent workflow

1. Create folder `deepagent/multiagent/legal_assistant/<intent_name>/`
2. Add `graph.py` with `build_graph()` returning compiled `StateGraph`
3. Add `nodes.py` with node implementations
4. Add intent to `IntentType` in `shared/state.py`
5. Register builder in `registry.py` `_GRAPH_BUILDERS`
6. Add routing rule in `api/apps/services/orchestration/intent_router.py`
7. Update `tools/policies.py` `INTENT_ALLOWED_TOOLS` if tools are used
8. Document in `docs/AGENTS.md`

### Avoid breaking existing graphs

- Do not change `LegalAssistantState` field semantics without updating all consumers
- Do not remove or rename nodes without updating all edges and conditional routes
- The **information** graph has a retry loop (`rag_iteration < 2`) — preserve routing in `route_after_reason`
- `task_execution` uses `interrupt()` — changes to HITL envelope must stay compatible with `format_graph_invoke_result()` and frontend
- Graphs are cached in `_GRAPH_CACHE` — restart API after graph changes during development

### HITL / checkpointing

- Only `task_execution` uses a LangGraph checkpointer (`InMemorySaver` in `shared/checkpointer.py`)
- HITL interrupts use `langgraph.types.interrupt` with payloads from `deepagent/core/hitl/checkpoint.py`
- Resume via `Command(resume=...)` with `thread_id` in config
- Session metadata stores `hitl_checkpoint` in PostgreSQL for thread_id recovery across requests
- Redis/Postgres checkpointer factories exist in `deepagent/core/check_pointers/base.py` but are **scaffolded, not implemented**
- HITL is lost on API restart (in-memory checkpointer limitation)

---

## RAG Development Rules

### Where retrieval logic lives

| Component | File |
|-----------|------|
| Retrieval service (search → rerank → LLM) | `api/apps/services/retrieval/service.py` |
| Citations | `api/apps/services/retrieval/citations.py` |
| ES hybrid search | `api/utils/elastic_chunk_index.py` (`LexChunkSearch`) |
| Agent-facing wrapper | `deepagent/multiagent/legal_assistant/tools/legal_retrieval.py` |
| Query expansion | `deepagent/core/query_rewriting/rewrite.py` (`requery_for_rag`) |
| Reranker | `deepagent/core/rerank/rerank.py` (`BAAI/bge-reranker-v2-m3`) |

### How Elasticsearch is used

- Index: `LEX_CHUNKS_INDEX` env var (default `lex_chunks_v1`)
- User documents: separate index via `api/utils/elastic_user_documents_index.py`
- **Keyword:** `multi_match` with field boosts (`article_title^8`, `subject_title^6`, `topic_title^5`, `content_text^2`)
- **Semantic:** KNN on `content_vector` (1024 dims, `AITeamVN/Vietnamese_Embedding_v2`)
- **Fusion:** `keyword_weight` (default 0.3) + semantic weight (0.7)
- **Post-filter:** similarity threshold (default 0.5), optional `topic_ids` / `subject_ids` filters

### How hybrid search works

```
Query → LexChunkSearch.search() → top candidate_size hits (default 100)
      → rerank_hits() → top final_size (default 5)
      → generate_answer_with_citations() → { answer with [n], cited_indexes }
      → build_references() → IEEE reference list (cited sources only)
```

### How reranking works

- FlagEmbedding `BAAI/bge-reranker-v2-m3` loaded at API startup when `RERANK_ENABLED=true`
- Reranker instance passed through state to avoid reloading per request
- If reranker unavailable, falls back to ES score ordering (logged as warning)

### Citation preservation rules

- LLM must return JSON with `answer` and `cited_indexes` (1-based)
- Only cited indexes appear in the `reference` panel — uncited chunks are excluded
- Web citations use separate format with `source_type: "web"`
- Never strip `[n]` inline citations from legal answers
- Never add fake references not present in retrieved chunks

### What NOT to do when modifying retrieval

- Do not bypass `build_references()` — it enforces cited-only references
- Do not hardcode legal article text as LLM context without ES retrieval
- Do not disable similarity threshold without understanding recall/precision impact
- Do not mix user-document and corpus indices without session strategy checks (`retrieval/session.py`)
- Do not assume reranker is always loaded — handle `RERANK_ENABLED=false` gracefully

---

## Document Generation Rules

### Where logic lives

```
deepagent/multiagent/legal_assistant/task_execution/
├── graph.py              # HITL workflow graph
├── nodes.py              # Template resolve, chunk assess, form fill, finalize
├── contract_tools.py     # DOCX render, MinIO upload
├── template_loader.py    # Load template from MinIO/DB
├── docx_field_extract.py # LLM field extraction from DOCX
├── hitl_groups.py        # Group fields for progressive fill
└── draft_preview.py      # Preview markdown + incremental save
```

API layer: `api/apps/services/contract_fill_service.py`, `contract_draft_session.py`

### Template handling

- Templates resolved from session uploads (`doc_ids`) or HITL template selection interrupt
- Two modes: `docx_native` (native DOCX field fill) and `markdown_reference` (chunk-based fill)
- Working DOCX bytes stored in graph state (`working_docx_bytes`)
- Final drafts uploaded to MinIO with version tracking

### HITL form filling rules

- Use `interrupt(build_hitl_interrupt(...))` — never block synchronously
- Resume payload parsed via `parse_human_resume()` in `checkpoint.py`
- Frontend sends `resume` object on `POST /v1/user/user_chat`
- Persist `hitl_checkpoint` in session metadata for thread_id recovery
- Form schema exposed to frontend via envelope `hitl` and `form_schema` fields

### DOCX generation rules

- Use `python-docx` via `contract_tools.py` — do not hand-craft OOXML
- Validate drafts via `validators.py` before finalize
- Preview available via `GET /v1/user/contract/draft/preview` endpoints

---

## Safety and Legal Disclaimer Rules

This is a **legal AI project**. Contributors and agents must follow these rules:

1. **Never present model output as official legal advice.** Responses are informational assistance only.
2. **Always preserve citations** when answering legal questions from the corpus. Inline `[n]` markers must map to the reference panel.
3. **Prefer uncertainty over unsupported claims.** Use cautious language when context is insufficient.
4. **Do not remove legal source references** from retrieval payloads or persisted messages.
5. **Do not hardcode fake legal answers** or fabricated article citations.
6. **Uncited fallback** (`compose_uncited_fallback`) must include an explicit disclaimer — do not remove it.
7. **Web sources** are supplementary — answers must note they require verification against official legal texts.
8. **Calculator outputs** are placeholders (`estimate_fine_range` returns `min: None, max: None`) — never present as computed penalties.

---

## Common Mistakes to Avoid

| Mistake | Correct approach |
|---------|------------------|
| Running `python api/lex_companion_server.py` | Use `uv run --env-file .env python -m api.lex_companion_server` |
| Using `pip install -e .` | Use `uv sync` from repo root |
| Using SQLAlchemy | Use Peewee ORM (`api/db/models.py`) |
| Pointing `langgraph.json` at legacy `legal_agent.agent:graph` | Use `deepagent/multiagent/legal_assistant/` graphs |
| Adding ReAct tool-calling agents | Tools are invoked directly in nodes via `tools/legal_retrieval.py` etc. |
| Hardcoding credentials in code | Use `.env` variables; never commit secrets |
| Bypassing retrieval for legal Q&A | Route through `run_legal_retrieval()` → ES → rerank → cited LLM |
| Removing citation logic to "simplify" answers | Citations are a core product requirement |
| Mixing Vietnamese legal source content with unsourced LLM claims | Separate grounded (cited) from uncited fallback paths |
| Expecting HITL to survive API restart | InMemorySaver only — document this limitation; persistent checkpointer is scaffolded |
| Editing `LegalAssistantState` without updating all graphs | Check all 6 intent folders + orchestrator |
| Creating API logic in routers | Follow Router → Controller → Service layering |
| Using wrong Docker ports locally | Dev API: 5999; Docker API: 6000; Dev Web: 3004; Docker Web: 3005 |

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Full technical architecture |
| [docs/AGENTS.md](docs/AGENTS.md) | Agent system reference for contributors |
| [api_creating_instruction.md](api_creating_instruction.md) | API development conventions |
| [README.md](README.md) | Quick start and feature overview |

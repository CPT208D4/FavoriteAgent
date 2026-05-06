# KnowledgeBase

**Source code repository (group):** [github.com/CPT208D4/FavoriteAgent](https://github.com/CPT208D4/FavoriteAgent)

**Deployed frontend (demo):** [https://pockety-three.vercel.app](https://pockety-three.vercel.app)

This repository contains a **FastAPI** backend for a personal knowledge / favorites store (**SQLite** + **ChromaDB**, **RAG**, optional **reranking**, **OpenAI-compatible** embeddings and chat APIs) and a **static HTML/CSS/JavaScript** frontend under `FavoriteAgent-frontend-pockety/`. The UI was produced from **Figma** designs, implemented as static pages, then wired with `fetch` to the API and optimized for interaction and performance; the live demo is hosted on **Vercel** at the URL above. The API must be deployed separately and configured in the frontend (and **CORS** must allow the Vercel origin if the API is on another host).

**AI-assisted development:** This repo includes an [`ai-logs/`](ai-logs/) folder with primary prompts used for core components (see [`ai-logs/README.md`](ai-logs/README.md)), including **in-app LLM strings** that mirror the code exactly ([`ai-logs/in-app-llm-system-prompts.md`](ai-logs/in-app-llm-system-prompts.md)).

---

## Features

| Area | Description |
|------|-------------|
| Documents | `GET` / `POST` / `PATCH` / `DELETE` `/documents`; ingest triggers chunking + embeddings |
| Auto category & tags | If `category` or `tags` are empty on create, an LLM infers them (English bookmark-style categories; see below) |
| File upload | `POST /documents/upload` accepts `.txt`, `.md`, `.csv`, `.pdf`, `.docx`, then indexes like normal creates |
| Seed data | `data/documents.json` + `scripts/init_data.py` import or update rows |
| Retrieval | `POST /retrieve`: query → embedding → Chroma top-k |
| Optional rerank | Enable in `.env` to rerank candidates from retrieval |
| Q&A | `POST /chat/ask`: retrieved chunks + `POST /v1/chat/completions` |
| Weekly report | `GET /reports/weekly`: last 7 days (UTC); English report; on LLM failure a non-model fallback is returned with `used_fallback: true` |
| Ops | `POST /admin/reindex-all`; `GET /export/rag-chunks` for debugging |

---

## Technologies used

**Backend**

- **Python** 3.10+
- **FastAPI** — HTTP API
- **Uvicorn** — ASGI server
- **Pydantic** / **pydantic-settings** — schemas and configuration
- **SQLAlchemy** — ORM
- **SQLite** — document metadata and content (`data/kb.sqlite`)
- **ChromaDB** — vector index (`data/chroma/`)
- **sentence-transformers** (when `EMBEDDING_BACKEND=local`) or **OpenAI-compatible** `/v1/embeddings` over **httpx**
- **httpx** — embedding, LLM, and optional rerank HTTP calls
- **PyPDF**, **python-docx**, **python-multipart** — upload parsing and forms

**Frontend**

- **HTML5**, **CSS3**, **vanilla JavaScript** (no React / Vue / Three.js in this repo)
- **Figma** — original UI design; pages under `FavoriteAgent-frontend-pockety/` implement those layouts as static assets
- **Vercel** — hosting for the public demo at [pockety-three.vercel.app](https://pockety-three.vercel.app)

---

## Prerequisites

- **Python 3.10+** (uses modern typing such as `list[str]`, `str | None`)
- For **API embeddings**: a reachable embedding endpoint and API key
- For **`/chat/ask`**, **classification**, and **reports**: a reachable **LLM** (OpenAI-compatible `/v1/chat/completions`)

---

## Setup

### 1. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 2. Environment variables

Copy the example file and fill in values from your provider’s docs. **Do not commit a real `.env` with secrets.**

```powershell
Copy-Item .env.example .env
```

Important: for embeddings, `EMBEDDING_API_BASE` should normally end at `.../v1`, **not** `.../v1/embeddings`. See the table below and `.env.example`.

### 3. Seed data (optional)

Import `data/documents.json` and build the index:

```bash
python scripts/init_data.py
```

### 4. Run the API

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Optional dev reload (large trees can make reload slow; narrow watch dirs or skip `--reload`):

```bash
python -m uvicorn app.main:app --reload --reload-dir app --reload-dir scripts --reload-dir data --host 127.0.0.1 --port 8000
```

### 5. Run the static frontend locally

In another terminal:

```bash
cd FavoriteAgent-frontend-pockety
python -m http.server 5500
```

Example pages (adjust port if you use another):

- `http://127.0.0.1:5500/home.html`
- `http://127.0.0.1:5500/favorites-travel.html`
- `http://127.0.0.1:5500/ai-assistant.html`
- `http://127.0.0.1:5500/weekly-report.html`

Point the frontend’s API base URL at `http://127.0.0.1:8000` (or your deployed API) as implemented in each page’s JavaScript.

### 6. Deployed demo vs local backend

- **Public UI:** [https://pockety-three.vercel.app](https://pockety-three.vercel.app) serves the static frontend from the CDN.
- **API:** must run on your own host (cloud VM, etc.). Configure the frontend to call that base URL and enable **CORS** on FastAPI for `https://pockety-three.vercel.app` if you use browser `fetch` cross-origin.
- For **full functionality** (chat, weekly report, uploads), the backend must be reachable with valid embedding/LLM keys in its environment.

### 7. API docs (local or deployed API)

- Swagger UI: `http://127.0.0.1:8000/docs` (replace host/port with your server)
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

There is no HTML page at `/`; use `/docs`.

---

## Where data lives

| Path | Purpose |
|------|---------|
| `data/kb.sqlite` | Primary DB: titles, body, category, tags, etc. |
| `data/chroma/` | Vector store for chunked embeddings |
| `data/documents.json` | Seed file for `init_data.py` only; not auto-synced both ways with SQLite |

**Ways to add content:** (1) `POST /documents` — recommended for day-to-day use; (2) edit `documents.json` and run `scripts/init_data.py` (same `id` updates); (3) `POST /documents/upload` with form field `file` and optional metadata.

If you change the **embedding model or dimension**, delete `data/chroma` and re-run `init_data.py` or `POST /admin/reindex-all`.

---

## Auto classification (bookmark categories)

When **`category` or `tags` are empty** on create, `app/services/classification.py` fills them. Categories are a **fixed English list**: `Science`, `Technology`, `Industry`, `Game`, `City`, `Sports`, `Business`, `Arts & Culture`, `Education`, `Health`, `Lifestyle`, `Entertainment`, `News & Media`, `Other`. If the LLM fails, keyword rules apply. Existing rows are not retro-updated unless you edit or re-save them.

---

## Weekly report (`GET /reports/weekly`)

1. **Window:** documents with non-null `created_at` in the **last 7 days**, compared in **UTC**.
2. **Cap:** up to **`REPORT_MAX_DOCS`** (default **12**), newest first (database-side filter).
3. **Prompt material:** each item includes `[Item i/n]`, title, category, tags, and a **fair per-document body budget** so many items are represented (not only the first long document).
4. **Output:** English; first two sentences tuned for compact UI cards; optional `_sanitize_report_for_ui` pass; see `app/services/reporting.py` and [`ai-logs/in-app-llm-system-prompts.md`](ai-logs/in-app-llm-system-prompts.md).
5. **JSON:** `report` is the text; **`used_fallback: true`** means the LLM path failed and a deterministic outline was returned.

Tune `REPORT_*` in `.env` as needed.

---

## Environment variables (common)

Full examples: **`.env.example`**.

| Variable | Meaning |
|----------|---------|
| `DATABASE_URL` | SQLite URL; default `sqlite:///./data/kb.sqlite` |
| `CHROMA_DIR` | Chroma persistence directory |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Chunk length and overlap |
| `EMBEDDING_BACKEND` | `local` or `api` |
| `EMBEDDING_API_BASE` | OpenAI-compatible root, e.g. `https://host/v1` |
| `EMBEDDING_API_KEY` / `EMBEDDING_API_MODEL` | API key and model id |
| `RERANK_ENABLED` | `true` to call external rerank; set `RERANK_*` |
| `LLM_API_BASE` / `LLM_API_KEY` / `LLM_MODEL` | Chat model for Q&A, classification, reports |
| `LLM_TIMEOUT_SECONDS` / `LLM_CONNECT_TIMEOUT_SECONDS` / `LLM_RETRIES` | Read timeout, connect timeout, retries on transient timeouts |
| `REPORT_MAX_DOCS` | Max documents in weekly material |
| `REPORT_MAX_CHARS_PER_DOC` | Per-document body cap in the weekly prompt |
| `REPORT_MAX_TOTAL_CHARS` | Total cap for weekly prompt material |

If `LLM_API_BASE` / `LLM_API_KEY` are unset, they **fall back** to `EMBEDDING_API_BASE` / `EMBEDDING_API_KEY`.

---

## HTTP API summary

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/documents` | List; query params `category`, `tag`, `q` |
| POST | `/documents` | Create document (indexes automatically) |
| POST | `/documents/upload` | Upload `.txt` / `.md` / `.csv` / `.pdf` / `.docx` |
| GET | `/documents/{doc_id}` | Get one |
| PATCH | `/documents/{doc_id}` | Update (re-indexes) |
| DELETE | `/documents/{doc_id}` | Delete doc and vectors |
| GET | `/export/rag-chunks` | Merged text export (debug) |
| POST | `/admin/reindex-all` | Rebuild all vectors |
| POST | `/retrieve` | Semantic search; body: `query`, `top_k` |
| POST | `/chat/ask` | RAG Q&A; body: `question`, `top_k` |
| GET | `/reports/weekly` | Weekly summary JSON: `period`, `doc_count`, `report`, `used_fallback` |

---

## Prompts

Application prompts are defined in:

- `app/services/qa.py`
- `app/services/classification.py`
- `app/services/reporting.py`
- `app/services/llm.py` (`chat_completion`, `chat_completion_enforced_english`)

Verbatim documentation: [`ai-logs/in-app-llm-system-prompts.md`](ai-logs/in-app-llm-system-prompts.md). Restart the server after changing prompts.

---

## Project layout

```
KnowledgeBase/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── db_models.py
│   ├── schemas.py
│   ├── api/routers/       # documents, retrieval, chat, reports, ...
│   └── services/          # chunking, embedding, vector_store, retrieval, rerank, llm, qa, reporting, classification
├── ai-logs/               # vibe coding + exact in-app LLM prompts
├── data/                  # kb.sqlite, chroma/, documents.json
├── FavoriteAgent-frontend-pockety/   # Frontend
├── scripts/init_data.py
├── requirements.txt
├── .env.example
└── README.md
```

---


# Primary prompts used during development (vibe coding)

Representative prompts used with AI coding assistants to design, implement, and iterate on this project. The **frontend** section is expanded because the UI was derived from **Figma**, exported/rebuilt as static HTML, then made interactive and optimized.

---

## 1. Backend (FastAPI + SQLite + Chroma + RAG)

Build a Python **FastAPI** knowledge-base service for a “Pocket / favorites” style product:

- **Persistence:** SQLite for documents (`title`, `content`, `category`, `tags`, `created_at`, optional `source_url`).
- **Chunking:** configurable `chunk_size` / `chunk_overlap`; embed with either **local sentence-transformers** or an **OpenAI-compatible** `POST /v1/embeddings` endpoint.
- **Vectors:** ChromaDB on disk under `data/chroma/`; metadata should reference `doc_id` / chunk ids for traceability.
- **Search:** `POST /retrieve` — embed the query, query Chroma top-k, optional rerank hook.
- **RAG Q&A:** `POST /chat/ask` — retrieve chunks, build a labeled context string, call **`/v1/chat/completions`**, return answer plus source list (`doc_id`, `chunk_id`, distance, optional rerank score).
- **Config:** pydantic-settings loading `.env`; never commit secrets.
- **Seeding:** `data/documents.json` + `scripts/init_data.py` to bulk import or update by `id`.
- **Health:** `GET /health` for deployment checks.

---

## 2. File upload pipeline

Add **`POST /documents/upload`** (multipart `file` field). Support **`.txt`**, **`.md`**, **`.csv`**, **`.pdf`**, **`.docx`**. Extract plain text (PyPDF / python-docx / UTF-8); normalize line endings; reject or safely handle empty extraction. Reuse the **same ingestion path** as `POST /documents`: chunk → embed → upsert Chroma; return the created document payload.

---

## 3. Weekly report, classification, and resilience

- **`GET /reports/weekly`:** Query SQLite for documents in the **last 7 days** using **`created_at` in UTC**, cap count (`REPORT_MAX_DOCS`), build prompt material with **fair per-item character budget** so many short saves are not drowned out by one long doc. Ask the LLM for **plain English**, **no Markdown**, first **two sentences** suitable for separate UI cards; **sanitize** lightly so cards do not show fake “Summary:” labels. On any LLM failure (timeout, HTTP error, empty message), return HTTP **200** with a **structured fallback outline** and `used_fallback: true`.
- **Auto classification:** When `category` or `tags` are omitted on create, call the chat model with a **fixed English category enum** and require **JSON only** `{ "category", "tags" }`; validate against the allow-list; on failure use **keyword heuristics** (`classification.py`).
- **HTTP client:** Use **httpx** with separate **connect** vs **read** timeouts; **retry** only transient timeout/connect failures a limited number of times with backoff.

---

## 4. Frontend: Figma → HTML, “make it move”, optimize, deploy

### 4.1 Design handoff

We had **Figma** screens for Pocket / travel / AI assistant / weekly report flows. The goal was to **match layout, typography, spacing, and color** while staying within **static HTML + CSS + vanilla JS** (no React build step in-repo) so the demo stays easy to run and host.

### 4.2 From static mock to real pages

- Export or rebuild sections as **semantic HTML** (landmarks, headings, lists where appropriate).
- Move repeated UI into **consistent class names** and shared **CSS variables** (colors, radii, shadows) so global tweaks stay cheap.
- Replace placeholder copy with **real strings** and hook up **data attributes** or element IDs for scripts.

### 4.3 “Make it move” (interactivity)

- **Navigation / chrome:** active states, mobile-friendly menus or tabs if the design calls for them.
- **Forms:** validate API base URL or preset backend origin; show loading and error states on `fetch` (e.g. `/health`, `/chat/ask`, `/reports/weekly`).
- **Weekly report UI:** parse JSON (`period`, `doc_count`, `report`, `used_fallback`); split or style the first sentences for **highlight / detail cards** when the design requires it; surface `used_fallback` with a subtle notice so users know the outline is non-LLM.
- **AI assistant page:** chat transcript, optional markdown-safe rendering, link sources back to document ids if exposed by the API.
- Prefer **CSS transitions** / **small keyframe animations** for hover and panel open instead of heavy libraries.

### 4.4 Performance and polish

- **Images:** compress assets; lazy-load below-the-fold images if any.
- **CSS:** avoid huge unused rules; co-locate page-specific styles or use one thin shared `theme` file.
- **JS:** debounce search inputs; avoid blocking the main thread; handle **CORS** explicitly when the API is on another origin (backend must allow the Vercel origin if applicable).
- **A11y:** focus order, button labels, sufficient contrast vs Figma.


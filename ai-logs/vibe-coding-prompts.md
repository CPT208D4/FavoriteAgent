# Primary prompts used during development (vibe coding)

Representative prompts used with AI coding assistants to design, implement, and iterate on this project. The **frontend** section is expanded because the UI was derived from **Figma**, exported/rebuilt as static HTML, then made interactive and optimized.
---

## 1. Backend

**User**

> I’m doing a uni group project — a “Pocket / favorites” style knowledge base. Can you help me scaffold a **Python FastAPI** backend?
>
> I need SQLite to store documents: at least title, full content, category, tags, created_at, maybe source_url. When I add or update a doc it should **chunk** the text (configurable chunk size + overlap), **embed** it, and upsert into **Chroma** on disk under something like `data/chroma/`. Metadata on each chunk should include doc id / chunk id so I can cite sources later.
>
> Please add:
>
> - `POST /retrieve` — embed the user query, search Chroma top-k, return chunks with scores.
> - `POST /chat/ask` — same retrieval, then call an **OpenAI-compatible** `POST /v1/chat/completions` with the chunks in the prompt, return the answer **and** a list of sources (doc_id, chunk_id, distance; rerank score optional if we add rerank later).
> - Config via **pydantic-settings** + `.env`, and a **`.env.example`** without secrets.
> - `GET /health`.
> - A seed script `scripts/init_data.py` that reads `data/documents.json` and upserts by id.
>
> For embeddings: support either **local sentence-transformers** OR hitting **`/v1/embeddings`** on a configurable base URL. Same pattern for LLM base URL + key.

---

## 2. File upload

**User**

> Right now I only have JSON / POST body create. I need **`POST /documents/upload`** with multipart `file`. Please support **txt, md, csv, pdf, docx** — pull text with pypdf / python-docx / utf-8, then **reuse the exact same pipeline** as creating a document (chunk + embed + chroma) so I don’t duplicate logic. If extraction is empty return a clear 400.

---

## 3. Weekly report + auto tags (follow-up messages)

**User**

> Add **`GET /reports/weekly`**. Pull docs from SQLite where **created_at** is in the **last 7 days** (use UTC). Cap how many docs go into the prompt so we don’t blow the context window — and **don’t** let one huge doc eat the whole budget; spread characters across items so short saves still show up.
>
> Prompt the LLM for an **English** weekly write-up. Our frontend wants the **first two sentences** as separate “cards”, so the model should write plain text **without markdown** (no `**`, bullets, `#`). If the LLM times out or errors, still return **HTTP 200** with a **fallback** outline built from titles + short previews, and a JSON field like **`used_fallback: true`** so the UI can show a small notice.

**User (later)**

> Classification: if the client leaves **category** or **tags** empty on create, call the chat model once with a **fixed list of English folder names** (Science, Technology, … Other) and make it reply with **JSON only** `{"category":"...", "tags":[...]}`. If JSON is bad or the model fails, fall back to simple **keyword rules** in code — don’t block the request.

**User (later)**

> `/reports/weekly` keeps failing with read timeout from httpx. Bump **read timeout** vs **connect**, and **retry** a couple times on timeout / connection errors only. Don’t retry on 4xx from the provider.

---

## 4. Frontend — Figma to HTML (several separate prompts)

**User**

> I exported our **Figma** Pocket / travel / assistant screens to static HTML but the structure is messy. Can you **clean it up** into proper semantic HTML (header/main/nav where it makes sense), **one shared CSS** with variables for colors / radius / shadows so it still looks like the Figma, and keep everything **vanilla JS** — no Vite/React for this demo, we’re hosting static files on Vercel.

**User**

> The pages are dead — wire **`weekly-report.html`** to our backend: input or constant for **API base URL**, button calls **`GET /reports/weekly`**, show loading + error states. Parse JSON: `report`, `doc_count`, **`used_fallback`**. Design has two small cards for “highlight” and “detail” — use the **first two sentences** of `report` for those (or a simple split on `. ` if you need). If `used_fallback` is true show a muted line like “Generated offline from your saves.”

**User**

> **`ai-assistant.html`**: chat UI that POSTs to **`/chat/ask`** with `{ question, top_k }`, append assistant message, show **sources** from the response if any. Disable send while loading; show network errors in the thread.

**User**

> Can you add **light motion** only with CSS — hover states, maybe a 200ms transition on cards and buttons, nothing heavy. Images from Figma are huge; **compress** or resize what you can and lazy-load anything below the fold.

**User**

> Frontend is on **Vercel** (`pockety-three.vercel.app`) but API is elsewhere. I’m getting CORS errors — what do I add on **FastAPI** so `fetch` from the Vercel origin works? Also remind me what to put in the HTML for default API URL in prod vs local.

---

## 5. Local preview (quick message)

**User**

> How do I run the static folder locally? I’m on Windows — is `cd FavoriteAgent-frontend-pockety` then `python -m http.server 5500` enough to test against `localhost:8000`?

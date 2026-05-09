# Primary prompts used during development (vibe coding)

Representative prompts used with AI coding assistants to design, implement, and iterate on this project. The UI comes from **Figma**, rebuilt as static HTML/CSS/vanilla JS in **`FavoriteAgent-frontend-pockety/`**.

Below, prompts are grouped by **backend**, **frontend**, then **misc** (repo / team noise).

---

## Backend

### 1. Knowledge base scaffold

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

### 2. File upload

**User**

> Right now I only have JSON / POST body create. I need **`POST /documents/upload`** with multipart `file`. Please support **txt, md, csv, pdf, docx** — pull text with pypdf / python-docx / utf-8, then **reuse the exact same pipeline** as creating a document (chunk + embed + chroma) so I don’t duplicate logic. If extraction is empty return a clear 400.

---

### 3. Weekly report, classification, and HTTP client

**User**

> Add **`GET /reports/weekly`**. Pull docs from SQLite where **created_at** is in the **last 7 days** (use UTC). Cap how many docs go into the prompt so we don’t blow the context window — and **don’t** let one huge doc eat the whole budget; spread characters across items so short saves still show up.
>
> Prompt the LLM for an **English** weekly write-up. Our frontend wants the **first two sentences** as separate “cards”, so the model should write plain text **without markdown** (no `**`, bullets, `#`). If the LLM times out or errors, still return **HTTP 200** with a **fallback** outline built from titles + short previews, and a JSON field like **`used_fallback: true`** so the UI can show a small notice.

**User**

> Classification: if the client leaves **category** or **tags** empty on create, call the chat model once with a **fixed list of English folder names** (Science, Technology, … Other) and make it reply with **JSON only** `{"category":"...", "tags":[...]}`. If JSON is bad or the model fails, fall back to simple **keyword rules** in code — don’t block the request.

**User**

> `/reports/weekly` keeps failing with read timeout from httpx. Bump **read timeout** vs **connect**, and **retry** a couple times on timeout / connection errors only. Don’t retry on 4xx from the provider.

---

### 4. Deploy on Vercel (rewrites, writable dirs, lighter deps)

**User**

> I’m trying to put both the static site and the FastAPI app on **Vercel**. Can you show me a **`vercel.json`** pattern with **rewrites** so the browser can call something like `/api/...` without CORS hell? Right now my frontend and backend feel like two different planets.

**User**

> Backend crashes on Vercel because **SQLite / Chroma paths aren’t writable**. Can we force **`DATA_DIR`** or **`/tmp`** for runtime data and **mkdir -p** style create parents before opening the db? I don’t care if data resets on cold start for the demo — I just need it to **boot**.

**User**

> Our **`requirements.txt`** is huge because of **sentence-transformers**. For production can we **drop local embeddings** from the default install and only use the **HTTP embeddings API** so deploys start faster?

---

### 5. Auto-seed when the database is empty

**User**

> When someone opens the app with an **empty database** it looks broken. Can we **auto-run** the seed import on startup if there are zero documents — same JSON we already have — so the favorites disc has something to show?

---

### 6. Chat QA: English-only answers + more playful prompt

**User**

> **`/chat/ask`** sometimes returns Chinese because my saved snippets are mixed language. I need the **UI language to stay English**. Can you add a **second pass** or a hard rule in code that strips / rewrites any CJK in the model output?

**User**

> The **`qa.py`** system prompt works but feels boring. Can we make it a bit more **playful** (still grounded in chunks, still list **sources** at the end)? Don’t break the strict “only from retrieval” rule.

---

### 7. Upload classification tuning

**User**

> File upload works but sometimes **`category` ends up weird**. Can uploads **default category** the same way as manual create, and can we **tune classification** so PDF notes don’t all land in **Other**?

---

### 8. Embeddings, reindex, retrieval tuning

**User**

> I changed **`EMBEDDING_MODEL`** in `.env` and now retrieval quality is off. Do I have to **delete `data/chroma`** and call something like **`POST /admin/reindex-all`**, or is there a cheaper path for a class demo?

**User**

> For the demo, is **`top_k: 3`** too tight for `/chat/ask`? The answers feel like they’re missing context but I don’t want huge latency.

**User**

> I’m not using **rerank** yet — is it enough to bump **`retrieve_vector_candidates`** and keep **top_k** small, or will that just add noise?

---

### 9. When the LLM provider is down (`/chat/ask`)

**User**

> When the LLM provider is down, **`/chat/ask`** 500s and the chat page looks broken. Can we return a **friendly message in the JSON** (or 200 with a short apology + `used_fallback`) so the UI can show text instead of a dead thread?

---

## Frontend

### 1. Figma export → clean HTML + design tokens

**User**

> I exported our **Figma** Pocket / travel / assistant screens to static HTML but the structure is messy. Can you **clean it up** into proper semantic HTML (header/main/nav where it makes sense), **one shared CSS** with variables for colors / radius / shadows so it still looks like the Figma, and keep everything **vanilla JS** — no Vite/React for this demo, we’re hosting static files on Vercel.

---

### 2. Wire `weekly-report.html` and `ai-assistant.html`

**User**

> The pages are dead — wire **`weekly-report.html`** to our backend: input or constant for **API base URL**, button calls **`GET /reports/weekly`**, show loading + error states. Parse JSON: `report`, `doc_count`, **`used_fallback`**. Design has two small cards for “highlight” and “detail” — use the **first two sentences** of `report` for those (or a simple split on `. ` if you need). If `used_fallback` is true show a muted line like “Generated offline from your saves.”

**User**

> In **`ai-assistant.html`**, chat UI that POSTs to **`/chat/ask`** with `{ question, top_k }`, append assistant message, show **sources** from the response if any. Disable send while loading; show network errors in the thread.

---

### 3. Motion, assets, CORS, API base URL

**User**

> Can you add **light motion** only with CSS — hover states, maybe a 200ms transition on cards and buttons, nothing heavy. Images from Figma are huge; **compress** or resize what you can and lazy-load anything below the fold.

**User**

> Frontend is on **Vercel** (`pockety-three.vercel.app`) but API is elsewhere. I’m getting CORS errors — what do I add on **FastAPI** so `fetch` from the Vercel origin works? Also remind me what to put in the HTML for default API URL in prod vs local.

---

### 4. Local preview on Windows

**User**

> How do I run the static folder locally? I’m on Windows — is `cd FavoriteAgent-frontend-pockety` then `python -m http.server 5500` enough to test against `localhost:8000`?

---

### 5. Favorites page: loading overlay, disc refresh, remembered theme

**User**

> **`favorites-travel.html`** loads boards from **`GET /documents`** but there’s a flash of empty UI. Can you add a simple **full-screen “syncing…” overlay** with a spinner until the first fetch finishes?

**User**

> I added a new theme / document from the modal but the **rotating disc doesn’t update** until I refresh the whole page. After a successful POST can you **refetch** and rebuild the disc?

**User**

> Can we **persist** which theme/card I had selected (localStorage is fine) so when I come back I’m not always reset to the first board?

---

### 6. Toast placement & duration + `report-summary.html` mascot

**User**

> Success toast is floating in a random corner. Can you **pin** it to the white “shell” card so it moves with the layout? Also leave it on screen **long enough to read** (~a few seconds).

**User**

> On **`report-summary.html`** there’s a little **AI mascot image** that looks clickable but does nothing — either wire it or **hide it** so users don’t tap dead UI.

---

### 7. Live data on history / weekly / summary pages

**User**

> **`history-report.html`** has “this week” tag chips that are still static. Can you **`fetch /documents`**, filter to the **last 7 days**, count by **category**, and fill the top two tags so it’s not fake text?

**User**

> Same idea for **`weekly-report.html`** — the tag cloud and week cards should **reflect real categories** from the API when the backend is up, and **fail quietly** to the Figma copy if the request fails.

**User**

> **`report-summary.html`** is supposed to feel like a **drill-down** from the weekly report. Can you pull **`GET /reports/weekly`** and split the first couple of sentences for the highlight/detail cards, and show a **sensible empty state** if `doc_count` is 0?

---

### 8. Bottom navigation consistency

**User**

> Our bottom bar icons don’t match what they do — on some pages the **second tab** went to history instead of **travel favorites**. Can you make the **mapping consistent** across HTML files, and on the **current page tab** can we do **press animation only** (no navigation) like iOS?

---

## Misc (repo & teammates)

### 1. Almost committing `.env`

**User**

> I keep almost committing **`.env`**. Can you double-check **`.gitignore`** and add a one-line comment in **`.env.example`** that says “copy to .env, never commit”?

---

### 2. Line endings Mac vs Windows

**User**

> Teammate’s on a Mac, I’m on Windows — are we going to fight over **line endings** in HTML forever or is that harmless?

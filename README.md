# KnowledgeBase Backend

知识库后端：**SQLite** 存文档、**Chroma** 存向量、**语义检索（RAG）**、可选 **rerank**、**OpenAI 兼容** 的问答与周报。

---

## 功能概览

| 能力 | 说明 |
|------|------|
| 文档管理 | `GET/POST/PATCH/DELETE /documents`，入库时自动分块 + 向量化 |
| 自动分类与标签 | 未填 `category` 或 `tags` 时调用 LLM 推断；类目为英文收藏夹风格（见下文） |
| 文件上传 | `POST /documents/upload` 支持 `.txt/.md/.csv/.pdf/.docx` 后自动入库与索引 |
| 批量种子 | `data/documents.json` + `scripts/init_data.py` 导入或更新 |
| 语义检索 | `POST /retrieve`：query → embedding → Chroma Top-K |
| 可选 rerank | `.env` 开启后先多路召回再调用外部 rerank API |
| 问答 | `POST /chat/ask`：检索片段 + `POST /v1/chat/completions` |
| 周报总结 | `GET /reports/weekly`：最近 7 天（UTC）、英文周报；失败时返回本地兜底摘要 |
| 运维 | `POST /admin/reindex-all` 全量重建向量；`GET /export/rag-chunks` 调试导出 |

---

## 技术栈

- **FastAPI** + **Uvicorn**
- **SQLAlchemy** + **SQLite**（`data/kb.sqlite`）
- **ChromaDB**（`data/chroma/`）
- **sentence-transformers**（`EMBEDDING_BACKEND=local`）或 **HTTP**（OpenAI 兼容 `/v1/embeddings`）
- **httpx** 调用 embedding / LLM / rerank

---

## 环境要求

- **Python 3.10+**（使用了 `list[str]`、`str | None` 等写法）
- 使用 **API 嵌入**时：需可用的 Embedding 网关与 Key
- 使用 **`/chat/ask`、reports** 时：需可用的 **LLM**（OpenAI 兼容 `/v1/chat/completions`）

---

## 快速开始

### 1. 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 2. 配置环境变量

复制模板并按供应商文档填写（**不要把含真实 Key 的 `.env` 提交到 Git**）：

```bash
# Windows CMD
copy .env.example .env

# PowerShell
Copy-Item .env.example .env
```

关键项见下文「环境变量说明」。**Embedding 的 `EMBEDDING_API_BASE` 一般只写到 `.../v1`，不要写到 `.../v1/embeddings`。**

### 3. 初始化数据（可选）

将 `data/documents.json` 导入数据库并建索引：

```bash
python scripts/init_data.py
```

### 4. 启动后端服务

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

开发时若需热重载，目录较大时可能卡顿，可限制监控范围或不用 `--reload`：

```bash
python -m uvicorn app.main:app --reload --reload-dir app --reload-dir scripts --reload-dir data --host 127.0.0.1 --port 8000
```

### 5. 启动前端静态页面（联调时推荐）

在**新终端**进入前端目录后运行：

```bash
cd FavoriteAgent-frontend-pockety
python -m http.server 5500
```

然后访问例如：

- <http://127.0.0.1:5500/home.html>
- <http://127.0.0.1:5500/favorites-travel.html>
- <http://127.0.0.1:5500/ai-assistant.html>

### 6. 打开接口文档

- **Swagger UI**：<http://127.0.0.1:8000/docs>（在线试接口）
- **ReDoc**：<http://127.0.0.1:8000/redoc>
- **OpenAPI JSON**：<http://127.0.0.1:8000/openapi.json>

根路径 `/` 无页面，访问 `/docs` 即可。

---

## 数据存哪里

| 路径 | 作用 |
|------|------|
| `data/kb.sqlite` | **运行时主库**：标题、正文、分类、标签等；`GET /documents` 读这里 |
| `data/chroma/` | **向量索引**：分块后的向量与元数据，供 `POST /retrieve` 使用 |
| `data/documents.json` | **种子文件**：仅执行 `init_data.py` 时导入；与数据库**不会自动双向同步** |

**添加内容三种方式：**

1. **推荐日常**：`POST /documents`（直接写入 SQLite 并更新向量）。
2. **批量手写**：改 `documents.json` 后运行 `python scripts/init_data.py`（同 `id` 会更新）。
3. **文件上传**：`POST /documents/upload`，表单字段包含 `file`，可选 `title/category/tags/source_url`。

若更换 **embedding 模型或维度**，建议删除 `data/chroma` 后重新 `init_data` 或调用 `POST /admin/reindex-all`。

---

## 自动分类（收藏夹类目）

新建文档时，若 **`category` 或 `tags` 留空**，会调用 `app/services/classification.py` 推断并写回数据库。类目为**固定英文列表**（便于与收藏夹/导出一致），例如：

`Science`，`Technology`，`Industry`，`Game`，`City`，`Sports`，`Business`，`Arts & Culture`，`Education`，`Health`，`Lifestyle`，`Entertainment`，`News & Media`，`Other`。

LLM 不可用时走关键词兜底。已入库的旧文档**不会自动改类目**；若需更新，可 `PATCH /documents/{id}` 手改或触发重新保存逻辑。

---

## 周报（`/reports/weekly`）如何工作

1. **时间范围**：`created_at` 在 **最近 7 天**内（与服务器 **UTC** 时间比较），`created_at` 为空的条目**不会纳入**。
2. **条数上限**：默认最多 **`REPORT_MAX_DOCS`**（默认 12）条，按 **`created_at` 从新到旧**。
3. **拼进模型的材料**：每条包含标题、分类、标签、正文片段；正文按**总长度上限**在条目间**均分预算**，避免只有前几篇占满上下文。
4. **生成语言**：系统提示要求输出**英文**周报，并尽量**覆盖材料中的每一条**（正文中带 `[Item i/n]` 标记）。
5. **响应字段**：`report` 为正文；`used_fallback=true` 表示 LLM 调用失败，返回的是根据元数据拼出的**兜底摘要**（非模型生成）。

相关环境变量（见下表 `REPORT_*`）可在 `.env` 中覆盖。

---

## 环境变量说明

完整示例见仓库根目录 **`.env.example`**。常用项：

| 变量 | 含义 |
|------|------|
| `DATABASE_URL` | SQLite 连接串，默认 `sqlite:///./data/kb.sqlite` |
| `CHROMA_DIR` | Chroma 持久化目录 |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 分块长度与重叠 |
| `EMBEDDING_BACKEND` | `local` 或 `api` |
| `EMBEDDING_API_BASE` | OpenAI 兼容根地址，如 `https://xxx/v1` |
| `EMBEDDING_API_KEY` / `EMBEDDING_API_MODEL` | API Key 与模型名 |
| `RERANK_ENABLED` | `true` 时启用外部 rerank，并配置 `RERANK_*` |
| `LLM_API_BASE` / `LLM_API_KEY` / `LLM_MODEL` | 问答、自动分类、周报使用的聊天模型 |
| `LLM_TIMEOUT_SECONDS` / `LLM_CONNECT_TIMEOUT_SECONDS` / `LLM_RETRIES` | LLM 读超时、连接超时、超时类错误重试次数 |
| `REPORT_MAX_DOCS` | 周报最多纳入多少条文档（默认 12） |
| `REPORT_MAX_CHARS_PER_DOC` | 周报材料里单条正文片段上限（字符） |
| `REPORT_MAX_TOTAL_CHARS` | 周报材料总字符上限（多文档时会在条间均分） |

未设置 `LLM_API_BASE` / `LLM_API_KEY` 时，会**回退使用** `EMBEDDING_API_BASE` / `EMBEDDING_API_KEY`（同一网关时常用）。

---

## HTTP 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/documents` | 列表，支持 `category`、`tag`、`q` 查询参数 |
| POST | `/documents` | 新建文档（自动索引） |
| POST | `/documents/upload` | 上传并解析文件：`.txt/.md/.csv/.pdf/.docx`（自动索引） |
| GET | `/documents/{doc_id}` | 单条 |
| PATCH | `/documents/{doc_id}` | 更新（会重索引） |
| DELETE | `/documents/{doc_id}` | 删除文档及对应向量 |
| GET | `/export/rag-chunks` | 全量合并文本导出（调试） |
| POST | `/admin/reindex-all` | 全量重建向量 |
| POST | `/retrieve` | 语义检索，`body`: `query`, `top_k` |
| POST | `/chat/ask` | RAG 问答，`body`: `question`, `top_k` |
| GET | `/reports/weekly` | 最近 7 天文档周报；JSON 含 `period`、`doc_count`、`report`、`used_fallback` |


---

## 提示词（Prompt）设计

本项目核心提示词用于：问答命中、问答未命中兜底、自动分类、周报总结。修改后需**重启服务**。

### 1) RAG 问答提示词（`POST /chat/ask`）

当检索到 `chunks` 时，后端在 `app/services/qa.py` 中使用如下 system prompt：

```text
你是严谨的知识库问答助手。只能基于提供的检索片段回答。
规则：
1) 先直接回答，再给出2-4条要点。
2) 不能编造片段外事实；不确定就明确说“不确定”。
3) 回答末尾附“引用来源”并列出 doc_id / chunk_id。
```

对应 user prompt 结构：

```text
问题：{question}

检索片段：
{context}
```

其中 `{context}` 由检索结果拼接，格式类似：

```text
[doc_id=... chunk_id=... title=...]
<chunk 文本>
```

### 2) 问答未命中兜底提示词

当检索结果为空时（`used_fallback=true`），使用如下提示词：

```text
你是知识库助手。当前知识库没有检索到相关片段。请礼貌地说明未命中，并建议用户换关键词或先补充知识库内容。
```

### 3) 自动分类提示词（`POST /documents` 等）

见 `app/services/classification.py`：要求模型从固定英文类目中选一项，并输出 JSON（`category` + `tags`）。

### 4) 周报总结提示词（`/reports/weekly`）

见 `app/services/reporting.py`：要求基于材料输出**英文**周报，并强调**每条收藏至少被提到一次**（材料中带 `[Item i/n]`）。user 侧会附带统计周期与条目数；以源码中的 `system` / `user` 字符串为准（若与旧文档示例不一致，以代码为准）。

### 5) 如何调整提示词

直接改下面文件中的字符串常量：

- `app/services/qa.py`（问答与兜底）
- `app/services/classification.py`（自动分类）
- `app/services/reporting.py`（周报）

改完后重启服务生效：

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## 项目结构（简要）

```
KnowledgeBase/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── db_models.py
│   ├── schemas.py
│   ├── api/routers/       # documents, retrieval, chat, reports
│   └── services/          # content, chunking, classification, embedding, vector_store, retrieval, rerank, llm, qa, reporting
├── data/                  # kb.sqlite, chroma/, documents.json
├── scripts/init_data.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 常见问题

**1. `POST /retrieve` 或 `/chat/ask` 报 5xx，终端里是 Embedding HTTP 503**  
多为供应商网关/额度/权限或临时故障。可用控制台同款 `curl` 测 `.../v1/embeddings`；恢复后重启服务。若曾换过 embedding 模型，清空 `data/chroma` 并重建索引。

**2. `GET /reports/weekly` 返回 `doc_count: 0`**  
周报按文档 **`created_at` 在最近 7 天内（UTC）**筛选；种子数据若日期过旧会为空。新建一条或检查系统时间与时区。

**3. 周报内容不全**  
先看响应里的 **`doc_count`** 是否等于你预期条数。若相等但仍漏提某条，可调高 `REPORT_MAX_TOTAL_CHARS` 或略增 `REPORT_MAX_DOCS`；模型偶尔也会偏重某一主题，可再改 `reporting.py` 中的提示词加强「逐条覆盖」。

**4. `/docs` 很卡**  
少用全局 `--reload`，或 `--reload-dir` 只监控 `app`、`scripts`、`data`。

**5. `GET /` 404**  
本服务未提供首页，请访问 `/docs`。





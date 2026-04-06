# KnowledgeBase Backend

独立实现的知识库后端：**SQLite** 存文档、**Chroma** 存向量、**语义检索（RAG）**、可选 **rerank**、**OpenAI 兼容** 的问答与日报/周报。

---

## 功能概览

| 能力 | 说明 |
|------|------|
| 文档管理 | `GET/POST/PATCH/DELETE /documents`，入库时自动分块 + 向量化 |
| 文件上传 | `POST /documents/upload` 支持 `.txt/.md/.pdf/.docx` 后自动入库与索引 |
| 批量种子 | `data/documents.json` + `scripts/init_data.py` 导入或更新 |
| 语义检索 | `POST /retrieve`：query → embedding → Chroma Top-K |
| 可选 rerank | `.env` 开启后先多路召回再调用外部 rerank API |
| 问答 | `POST /chat/ask`：检索片段 + `POST /v1/chat/completions` |
| 周期总结 | `/reports/daily`、`/reports/weekly`、`/reports/generate` |
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

复制模板并按供应商文档填写（**不要把真实 Key 提交到 Git**）：

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

### 4. 启动服务

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

开发时若需热重载，目录较大时可能卡顿，可限制监控范围或不用 `--reload`：

```bash
python -m uvicorn app.main:app --reload --reload-dir app --reload-dir scripts --reload-dir data --host 127.0.0.1 --port 8000
```

### 5. 打开接口文档

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
| `LLM_API_BASE` / `LLM_API_KEY` / `LLM_MODEL` | 问答与报告使用的聊天模型 |

未设置 `LLM_API_BASE` / `LLM_API_KEY` 时，会**回退使用** `EMBEDDING_API_BASE` / `EMBEDDING_API_KEY`（同一网关时常用）。

---

## HTTP 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/documents` | 列表，支持 `category`、`tag`、`q` 查询参数 |
| POST | `/documents` | 新建文档（自动索引） |
| POST | `/documents/upload` | 上传并解析文件：`.txt/.md/.pdf/.docx`（自动索引） |
| GET | `/documents/{doc_id}` | 单条 |
| PATCH | `/documents/{doc_id}` | 更新（会重索引） |
| DELETE | `/documents/{doc_id}` | 删除文档及对应向量 |
| GET | `/export/rag-chunks` | 全量合并文本导出（调试） |
| POST | `/admin/reindex-all` | 全量重建向量 |
| POST | `/retrieve` | 语义检索，`body`: `query`, `top_k` |
| POST | `/chat/ask` | RAG 问答，`body`: `question`, `top_k` |
| GET | `/reports/daily` | 最近 1 天文档总结 |
| GET | `/reports/weekly` | 最近 7 天文档总结 |
| POST | `/reports/generate` | `body`: `days`, `max_docs` |

### 给 AI 同学对接（最小约定）

1. **`POST /retrieve`**：只拿上下文片段，自拼 Prompt 调模型。  
2. **`POST /chat/ask`**：由本服务完成检索 + 调用 LLM；响应含 `sources`（`doc_id`、`chunk_id`）便于溯源。

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
│   └── services/          # content, chunking, embedding, vector_store, retrieval, rerank, llm, qa, reporting
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

**2. `GET /reports/daily` 返回 `doc_count: 0`**  
日报按文档 **`created_at` 在最近 1 天内**筛选；种子数据若日期较旧会为空。可 `POST /documents` 新建一条，或 `POST /reports/generate` 增大 `days`。

**3. `/docs` 很卡**  
少用全局 `--reload`，或 `--reload-dir` 只监控 `app`、`scripts`、`data`。

**4. `GET /` 404**  
本服务未提供首页，请访问 `/docs`。



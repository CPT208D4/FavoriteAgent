# KnowledgeBase 从 0 到 1 新手说明（超详细）

这份文档是给**完全零基础**同学看的。目标是让你搞清楚：

1. 这个项目到底做了什么  
2. 你改哪里会影响什么  
3. 你如何继续维护、演示、答辩

---

## 0. 先一句话理解这个项目

你现在做的是一个**知识库后端服务**，它能：

- 把文本内容存起来（SQLite）
- 把文本切块并向量化（Embedding）
- 根据用户问题做语义检索（Chroma）
- 把检索结果给大模型生成回答（RAG）
- 按天/周生成总结（日报/周报）

你们当前没有做爬虫和完整前端，先把后端核心能力做出来了。

---

## 1. 你现在已经有的核心能力（结论先看）

你已经实现并测试通过：

- 文档 CRUD（增删改查）
- 文件上传入库（`.txt/.md/.pdf/.docx`）
- 语义检索 `POST /retrieve`
- 问答 `POST /chat/ask`
- 日报周报 `GET /reports/daily` / `GET /reports/weekly`
- 自动接口文档 `/docs`

所以对于“后端知识库 + RAG 基础链路”来说，已经是可运行版本。

---

## 2. 项目目录怎么读（每个文件在干嘛）

```text
KnowledgeBase/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── db_models.py
│   ├── schemas.py
│   ├── api/routers/
│   │   ├── documents.py
│   │   ├── retrieval.py
│   │   ├── chat.py
│   │   └── reports.py
│   └── services/
│       ├── content_service.py
│       ├── chunking.py
│       ├── embedding.py
│       ├── vector_store.py
│       ├── retrieval.py
│       ├── rerank.py
│       ├── llm.py
│       ├── qa.py
│       └── reporting.py
├── data/
│   ├── documents.json
│   ├── kb.sqlite
│   └── chroma/
├── scripts/
│   └── init_data.py
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

### 2.1 `app/main.py`
- FastAPI 入口。
- 启动时会 `init_db()`（确保数据库表存在）。
- 把各路由挂载进来（documents/retrieve/chat/reports）。

### 2.2 `app/config.py`
- 读取 `.env` 配置。
- 定义所有可调参数：数据库路径、chroma 路径、embedding 接口、llm 接口、chunk 大小等。

### 2.3 `app/database.py` + `app/db_models.py`
- `database.py`：SQLAlchemy 引擎/会话管理。
- `db_models.py`：定义 `documents` 表结构（id/title/content/tags 等）。

### 2.4 `app/schemas.py`
- 定义 API 的请求/响应数据结构（Pydantic）。
- Swagger (`/docs`) 里看到的字段说明来自这里。

### 2.5 `app/api/routers/*.py`
- `documents.py`：文档 CRUD、文件上传、导出、重建索引。
- `retrieval.py`：语义检索。
- `chat.py`：问答。
- `reports.py`：日报/周报/自定义总结。

### 2.6 `app/services/*.py`
- 业务逻辑核心都在这里：
  - `content_service.py`：入库、更新、删除、上传解析、触发索引
  - `chunking.py`：切块
  - `embedding.py`：本地模型 or API embedding
  - `vector_store.py`：写入/查询 Chroma
  - `retrieval.py`：检索流程
  - `llm.py`：调用聊天模型
  - `qa.py`：检索 + 拼上下文 + 问答
  - `reporting.py`：按时间筛文档并总结
  - `rerank.py`：可选重排序

### 2.7 `data/`
- `documents.json`：种子文件（批量导入源）。
- `kb.sqlite`：运行时主数据库（真正数据在这里）。
- `chroma/`：向量索引文件（检索时用）。

### 2.8 `scripts/init_data.py`
- 把 `documents.json` 导入 SQLite，并同时创建/更新向量索引。

---

## 3. 数据流到底怎么走（最关键）

这里是你答辩最该讲清楚的部分。

## 3.1 新增一条文档（`POST /documents`）

1. 请求进到 `documents.py`
2. 调用 `content_service.create_document()`
3. 写入 `kb.sqlite`（`documents` 表）
4. 把 `title + content` 拼成大文本
5. `chunking.py` 切块
6. `embedding.py` 把每个块变向量
7. `vector_store.py` 写进 `chroma`
8. 返回新增文档 JSON

也就是说：**一旦新增文档，向量索引是自动更新的。**

---

## 3.2 检索（`POST /retrieve`）

1. 用户传 `query`（问题）
2. 后端把 `query` 向量化
3. 去 `chroma` 做相似度检索 Top-K
4. 可选 rerank（如果开了）
5. 返回最相关片段 `chunks`

`chunks` 里有：
- `doc_id`
- `chunk_id`
- `title`
- `text`
- `distance`

---

## 3.3 问答（`POST /chat/ask`）

1. 先调用检索拿片段
2. 拼成上下文 prompt
3. 调 LLM（`/v1/chat/completions`）
4. 返回：
   - `answer`
   - `sources`（来源）
   - `used_fallback`（是否没命中走兜底）

这就是标准 RAG：**先检索，再生成。**

---

## 3.4 日报/周报（`/reports/*`）

1. 从 `kb.sqlite` 里按 `created_at` 筛最近 N 天文档
2. 把文档内容组织成上下文
3. 调 LLM 生成总结
4. 返回 `period/doc_count/report`

如果 `doc_count=0`，常见原因是你导入的数据日期太旧，不在“最近1天/7天”里。

---

## 4. `.env` 每一项是干嘛的（你最常改）

### 4.1 存储相关
- `DATABASE_URL`：SQLite 地址（通常不用改）
- `CHROMA_DIR`：向量文件目录

### 4.2 分块相关
- `CHUNK_SIZE`：每块多长
- `CHUNK_OVERLAP`：块与块重叠多少

### 4.3 Embedding 相关
- `EMBEDDING_BACKEND=api|local`
  - `api`：走云端接口
  - `local`：走本地 sentence-transformers
- `EMBEDDING_API_BASE`：一般写到 `.../v1`
- `EMBEDDING_API_KEY`
- `EMBEDDING_API_MODEL`（如 `bge-m3`）

### 4.4 LLM 相关
- `LLM_API_BASE`
- `LLM_API_KEY`
- `LLM_MODEL`

---

## 5. `documents.json` 和 `kb.sqlite` 的关系（最容易混）

很多新手会搞混这个：

- `documents.json` 是**导入源**
- `kb.sqlite` 是**运行时主库**

### 重点：
- 你用 API 新增文档 -> 会写进 `kb.sqlite`，不会自动写回 `documents.json`
- 你改了 `documents.json` -> 需要跑 `python scripts/init_data.py` 才会同步进数据库

所以你看到“上传成功但 JSON 没变”是完全正常的。

---

## 6. 现在如何添加知识库内容（3种方法）

### 方法 A（推荐）：Swagger 中 `POST /documents`
- 手工填 title/content/category/tags
- 适合日常新增

### 方法 B：文件上传 `POST /documents/upload`
- 支持 `.txt/.md/.pdf/.docx`
- 上传后自动解析并入库

### 方法 C：批量导入
- 改 `data/documents.json`
- 执行 `python scripts/init_data.py`

---

## 7. 你如何判断“真的成功了”

最小验证链路：

1. `GET /documents` 有新文档
2. `POST /retrieve` 能检索到你文档里的关键词
3. `POST /chat/ask` 回答里 `sources` 包含对应 `doc_id/chunk_id`

如果这三步都通过，说明链路是通的。

---

## 8. 常见错误与解决

## 8.1 `/retrieve` 500 + 终端是 embedding 503
- 多为供应商 API 网关问题/权限/额度问题
- 用供应商控制台 `curl` 先单测 `/v1/embeddings`

## 8.2 `/docs` 很卡
- 避免全量 `--reload`，或限制 `--reload-dir`

## 8.3 日报 `doc_count=0`
- 最近 1 天无新文档（`created_at` 太旧）

## 8.4 上传后出现重复文档
- 同一文件多次上传会新增多条（当前默认不去重）

---

## 9. 你可以怎么给同学对接（最简）

给同学两种接法：

### 接法 1（推荐简单）
- 同学只调用 `POST /chat/ask`
- 他拿 `answer + sources` 直接展示

### 接法 2（更灵活）
- 同学先调 `POST /retrieve`
- 再自行拼 prompt 调他的模型

---

## 10. 你目前完成度怎么说（答辩可用）

你可以这样表述：

> 已实现知识库后端核心能力：文档管理、文件上传、向量化、语义检索、RAG问答、日报周报生成；并通过 FastAPI OpenAPI 文档完成接口自测和联调。当前未包含爬虫与平台登录能力，后续可在现有架构上扩展。

---

## 11. 给未来自己的建议（可选扩展）

后续可以逐步做：

1. 上传去重（文件哈希）
2. 文档来源字段（source_file）
3. 用户体系（多用户隔离）
4. 前端页面（而非只用 `/docs`）
5. 知识图谱抽取
6. 记忆卡片生成
7. 音频播客脚本自动生成

---

## 12. 最后一句

你现在已经不是“啥都没做”的状态了。  
你已经把一套**能跑、能检索、能问答、能总结**的知识库后端搭起来了，这就是一个完整的工程里程碑。


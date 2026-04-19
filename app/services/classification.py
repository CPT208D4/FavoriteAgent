import json
import re

from . import llm

_CATEGORIES = [
    "人工智能",
    "编程开发",
    "数据结构与算法",
    "学习方法",
    "产品与设计",
    "商业与运营",
    "其他",
]


def _keyword_fallback(text: str) -> tuple[str, list[str]]:
    t = text.lower()
    tags: list[str] = []
    if any(k in t for k in ["rag", "embedding", "llm", "prompt", "向量", "检索"]):
        return "人工智能", ["RAG", "Embedding", "LLM"]
    if any(k in t for k in ["python", "fastapi", "sql", "api", "后端", "数据库"]):
        return "编程开发", ["Python", "API", "Backend"]
    if any(k in t for k in ["栈", "队列", "链表", "树", "图", "dfs", "bfs", "算法"]):
        return "数据结构与算法", ["数据结构", "算法"]
    if any(k in t for k in ["复盘", "学习", "记忆", "习惯", "效率"]):
        return "学习方法", ["学习方法"]
    return "其他", tags


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def infer_category_and_tags(title: str, content: str) -> tuple[str, list[str]]:
    base = f"{title}\n\n{content}"[:4000]
    system = (
        "你是知识库内容分类器。请将输入内容分类并打标签。\n"
        "只能从以下分类中选一个："
        + "、".join(_CATEGORIES)
        + "\n"
        "输出严格 JSON，格式："
        '{"category":"分类名","tags":["标签1","标签2","标签3"]}'
    )
    user = f"请分类并打标签：\n{base}"
    try:
        out = llm.chat_completion(system, user)
        obj = _extract_json(out)
        if not obj:
            return _keyword_fallback(base)
        category = str(obj.get("category", "")).strip()
        if category not in _CATEGORIES:
            category = "其他"
        tags_raw = obj.get("tags", [])
        tags: list[str] = []
        if isinstance(tags_raw, list):
            for x in tags_raw:
                s = str(x).strip()
                if s and s not in tags:
                    tags.append(s)
        return category, tags[:8]
    except Exception:
        return _keyword_fallback(base)

import json
import re

from . import llm

# Bookmark-style folders: English labels for consistency with feeds / exports.
_CATEGORIES = [
    "Science",
    "Technology",
    "Industry",
    "Game",
    "City",
    "Sports",
    "Business",
    "Arts & Culture",
    "Education",
    "Health",
    "Lifestyle",
    "Entertainment",
    "News & Media",
    "Other",
]


def _keyword_fallback(text: str) -> tuple[str, list[str]]:
    t = text.lower()
    tags: list[str] = []
    if any(
        k in t
        for k in [
            "physics",
            "chemistry",
            "biology",
            "math",
            "research",
            "paper",
            "科学",
            "物理",
            "化学",
            "生物",
            "论文",
        ]
    ):
        return "Science", ["science"]
    if any(
        k in t
        for k in [
            "software",
            "hardware",
            "ai",
            "code",
            "github",
            "api",
            "芯片",
            "编程",
            "软件",
            "技术",
        ]
    ):
        return "Technology", ["tech"]
    if any(
        k in t
        for k in ["manufacturing", "supply chain", "factory", "工业", "制造", "产业"]
    ):
        return "Industry", ["industry"]
    if any(k in t for k in ["game", "gaming", "steam", "游戏", "电竞"]):
        return "Game", ["game"]
    if any(k in t for k in ["city", "urban", "metro", "城市", "旅游", "旅行"]):
        return "City", ["city"]
    if any(k in t for k in ["sport", "nba", "fifa", "足球", "篮球", "奥运"]):
        return "Sports", ["sports"]
    if any(k in t for k in ["startup", "finance", "market", "商业", "金融", "创业"]):
        return "Business", ["business"]
    if any(k in t for k in ["art", "music", "film", "设计", "艺术", "电影"]):
        return "Arts & Culture", ["culture"]
    if any(k in t for k in ["course", "tutorial", "learn", "学习", "课程", "教程"]):
        return "Education", ["education"]
    if any(k in t for k in ["health", "medical", "fitness", "健康", "医疗", "养生"]):
        return "Health", ["health"]
    if any(k in t for k in ["food", "recipe", "fashion", "生活", "美食", "穿搭"]):
        return "Lifestyle", ["lifestyle"]
    if any(k in t for k in ["movie", "show", "综艺", "娱乐", "影视"]):
        return "Entertainment", ["entertainment"]
    if any(k in t for k in ["news", "breaking", "头条", "新闻", "媒体"]):
        return "News & Media", ["news"]
    return "Other", tags


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
        "You classify bookmark / saved items. Pick exactly ONE category from the list.\n"
        "Categories (use the string verbatim): "
        + ", ".join(_CATEGORIES)
        + "\n"
        "Reply with JSON only: "
        '{"category":"<one of the list>","tags":["short tag 1","tag 2","tag 3"]}\n'
        "Tags: 2–6 short tokens (English or Chinese), no duplicates."
    )
    user = f"Title + content to classify:\n{base}"
    try:
        out = llm.chat_completion(system, user)
        obj = _extract_json(out)
        if not obj:
            return _keyword_fallback(base)
        category = str(obj.get("category", "")).strip()
        if category not in _CATEGORIES:
            category = "Other"
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

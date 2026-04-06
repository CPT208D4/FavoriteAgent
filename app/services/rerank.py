import httpx

from ..config import settings


def rerank_chunks(query: str, rows: list[dict], top_k: int) -> list[dict]:
    """
    通用「Jina / Cohere 风格」rerank：POST JSON，响应含 results[].index 与 relevance_score。
    具体 URL、模型名以各云厂商文档为准。
    """
    if not rows:
        return []
    url = settings.rerank_api_url
    key = settings.rerank_api_key
    if not url or not key:
        raise RuntimeError(
            "rerank_enabled=true 时请在 .env 中设置 RERANK_API_URL 与 RERANK_API_KEY"
        )
    model = settings.rerank_model or "rerank-model"
    documents = [r.get("text") or "" for r in rows]
    with httpx.Client(timeout=float(settings.rerank_timeout_seconds)) as client:
        r = client.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "query": query, "documents": documents},
        )
        r.raise_for_status()
        data = r.json()
    results = data.get("results") or data.get("data") or []
    if not results:
        return rows[:top_k]
    scored: list[tuple[int, float]] = []
    for item in results:
        if isinstance(item, dict) and "index" in item:
            idx = int(item["index"])
            score = float(
                item.get("relevance_score")
                or item.get("score")
                or item.get("relevance")
                or 0.0
            )
            scored.append((idx, score))
    scored.sort(key=lambda x: -x[1])
    out: list[dict] = []
    for idx, score in scored[:top_k]:
        if 0 <= idx < len(rows):
            row = dict(rows[idx])
            row["rerank_score"] = score
            out.append(row)
    return out if out else rows[:top_k]

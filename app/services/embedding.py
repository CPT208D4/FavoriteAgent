from functools import lru_cache

import httpx

from ..config import settings


def _l2_normalize(vec: list[float]) -> list[float]:
    s = sum(x * x for x in vec) ** 0.5
    if s <= 0:
        return vec
    return [x / s for x in vec]


@lru_cache(maxsize=1)
def _local_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def _embed_local(texts: list[str]) -> list[list[float]]:
    model = _local_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.tolist()


def _embed_openai_compatible(texts: list[str]) -> list[list[float]]:
    base = (settings.embedding_api_base or "").rstrip("/")
    key = settings.embedding_api_key
    if not base or not key:
        raise RuntimeError(
            "embedding_backend=api 时请在环境变量或 .env 中设置 "
            "EMBEDDING_API_BASE（如 https://api.xxx.com/v1）与 EMBEDDING_API_KEY"
        )
    model = settings.embedding_api_model or "text-embedding-3-small"
    url = f"{base}/embeddings"
    out: list[list[float]] = []
    bs = max(1, settings.embedding_batch_size)
    with httpx.Client(timeout=120.0) as client:
        for i in range(0, len(texts), bs):
            batch = texts[i : i + bs]
            r = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "input": batch},
            )
            r.raise_for_status()
            data = r.json()
            items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
            for item in items:
                emb = item.get("embedding")
                if not isinstance(emb, list):
                    raise RuntimeError("嵌入 API 返回格式异常：缺少 embedding 列表")
                out.append(_l2_normalize([float(x) for x in emb]))
    return out


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if settings.embedding_backend == "api":
        return _embed_openai_compatible(texts)
    return _embed_local(texts)

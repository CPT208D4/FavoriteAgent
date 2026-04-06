from functools import lru_cache

import chromadb

from ..config import settings

COLLECTION = "knowledge_chunks"
_TITLE_MAX = 256


def _truncate_title(title: str) -> str:
    if len(title) <= _TITLE_MAX:
        return title
    return title[: _TITLE_MAX - 1] + "…"


@lru_cache(maxsize=1)
def _client() -> chromadb.PersistentClient:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_dir))


@lru_cache(maxsize=1)
def get_collection():
    return _client().get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def delete_by_doc_id(doc_id: str) -> None:
    col = get_collection()
    col.delete(where={"doc_id": doc_id})


def add_document_chunks(
    doc_id: str,
    title: str,
    chunk_texts: list[str],
    embeddings: list[list[float]],
) -> None:
    if not chunk_texts:
        return
    col = get_collection()
    t = _truncate_title(title)
    ids = [f"{doc_id}:{i}" for i in range(len(chunk_texts))]
    metadatas = [{"doc_id": doc_id, "chunk_index": i, "title": t} for i in range(len(chunk_texts))]
    col.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunk_texts,
        metadatas=metadatas,
    )


def query_chunks(query_embedding: list[float], top_k: int) -> list[dict]:
    col = get_collection()
    res = col.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    ids_batch = res.get("ids") or []
    docs_batch = res.get("documents") or []
    meta_batch = res.get("metadatas") or []
    dist_batch = res.get("distances") or []
    if not ids_batch or not ids_batch[0]:
        return []
    ids = ids_batch[0]
    docs = docs_batch[0] if docs_batch else []
    metas = meta_batch[0] if meta_batch else []
    dists = dist_batch[0] if dist_batch else []
    out: list[dict] = []
    for i, cid in enumerate(ids):
        meta = metas[i] if i < len(metas) and metas[i] else {}
        out.append(
            {
                "chunk_id": cid,
                "doc_id": str(meta.get("doc_id", "")),
                "title": str(meta.get("title", "")),
                "text": docs[i] if i < len(docs) and docs[i] is not None else "",
                "distance": float(dists[i]) if i < len(dists) else 0.0,
            }
        )
    return out

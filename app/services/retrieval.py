from ..config import settings
from ..schemas import ChunkHit, RetrieveResponse
from . import embedding, vector_store


def retrieve(query: str, top_k: int) -> RetrieveResponse:
    q_emb = embedding.embed_texts([query])[0]
    candidates = (
        max(settings.retrieve_vector_candidates, top_k)
        if settings.rerank_enabled
        else top_k
    )
    rows = vector_store.query_chunks(q_emb, candidates)
    if settings.rerank_enabled:
        from . import rerank

        rows = rerank.rerank_chunks(query, rows, top_k)
    else:
        rows = rows[:top_k]

    chunks = [
        ChunkHit(
            chunk_id=r["chunk_id"],
            doc_id=r["doc_id"],
            title=r["title"],
            text=r["text"],
            distance=r["distance"],
            rerank_score=r.get("rerank_score"),
        )
        for r in rows
    ]
    return RetrieveResponse(query=query, chunks=chunks)

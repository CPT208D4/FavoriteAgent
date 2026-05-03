from ..schemas import AskResponse, SourceItem
from . import llm, retrieval


def _build_context(chunks: list) -> str:
    parts: list[str] = []
    for c in chunks:
        parts.append(
            f"[doc_id={c.doc_id} chunk_id={c.chunk_id} title={c.title}]\n{c.text}"
        )
    return "\n\n---\n\n".join(parts)


def ask(question: str, top_k: int) -> AskResponse:
    ret = retrieval.retrieve(question, top_k)
    if not ret.chunks:
        fallback = (
            "You are a knowledge-base assistant. No relevant chunks were retrieved. "
            "Reply in English only. Politely explain that there is no hit, and suggest "
            "trying different keywords or adding more documents to the knowledge base."
        )
        answer = llm.chat_completion_enforced_english(fallback, question)
        return AskResponse(answer=answer, sources=[], used_fallback=True)

    context = _build_context(ret.chunks)
    system_prompt = (
        "You are a rigorous knowledge-base QA assistant. Reply in English only. "
        "You must answer strictly based on the provided retrieved chunks. "
        "Use a lightly warm, slightly playful tone (a small touch of personality), "
        "but stay professional, concise, and never let style override accuracy.\n"
        "Rules:\n"
        "1) Start with a direct answer, then provide 2-4 concise bullet points.\n"
        "2) Do not invent facts outside the chunks; if uncertain, explicitly say you are uncertain.\n"
        "3) End with a 'Sources' section and list doc_id / chunk_id."
    )
    user_prompt = f"Question: {question}\n\nRetrieved chunks:\n{context}"
    answer = llm.chat_completion_enforced_english(system_prompt, user_prompt)
    sources = [
        SourceItem(
            doc_id=c.doc_id,
            chunk_id=c.chunk_id,
            title=c.title,
            distance=c.distance,
            rerank_score=c.rerank_score,
        )
        for c in ret.chunks
    ]
    return AskResponse(answer=answer, sources=sources, used_fallback=False)

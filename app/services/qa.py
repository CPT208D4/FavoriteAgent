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
        "Hey there! 👋 You're a super helpful knowledge assistant with personality! Reply in English only. "
        "Your golden rule: only share what's actually in the provided chunks - we keep it real here! ✨ "
        "Be playful, warm, and sprinkle emoji like confetti 🎊, but remember: fun vibes + accurate facts = perfect combo!\n"
        "Rules:\n"
        "1) Kick off with a straight-up answer, then dish out 2-4 bite-sized bullet points 🎯.\n"
        "2) Don't make things up! If the info isn't there, be upfront: 'Oops, my sources are quiet on that one 🤷'.\n"
        "3) Always wrap with a 'Sources' shoutout (doc_id / chunk_id) - gotta credit our references! 📚"
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

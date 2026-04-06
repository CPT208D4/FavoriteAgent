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
            "你是知识库助手。当前知识库没有检索到相关片段。"
            "请礼貌地说明未命中，并建议用户换关键词或先补充知识库内容。"
        )
        answer = llm.chat_completion(fallback, question)
        return AskResponse(answer=answer, sources=[], used_fallback=True)

    context = _build_context(ret.chunks)
    system_prompt = (
        "你是严谨的知识库问答助手。只能基于提供的检索片段回答。"
        "规则：\n"
        "1) 先直接回答，再给出2-4条要点。\n"
        "2) 不能编造片段外事实；不确定就明确说“不确定”。\n"
        "3) 回答末尾附“引用来源”并列出 doc_id / chunk_id。"
    )
    user_prompt = f"问题：{question}\n\n检索片段：\n{context}"
    answer = llm.chat_completion(system_prompt, user_prompt)
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

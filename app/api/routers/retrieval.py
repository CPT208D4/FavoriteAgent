from fastapi import APIRouter

from ...schemas import RetrieveRequest, RetrieveResponse
from ...services.retrieval import retrieve

router = APIRouter(tags=["retrieval"])


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve_chunks(body: RetrieveRequest):
    """语义检索：根据问题返回最相关的文本块，供大模型作为上下文。"""
    return retrieve(query=body.query, top_k=body.top_k)

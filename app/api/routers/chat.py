from fastapi import APIRouter, HTTPException

from ...schemas import AskRequest, AskResponse
from ...services import qa

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=AskResponse)
def ask_question(body: AskRequest):
    try:
        return qa.ask(question=body.question, top_k=body.top_k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"问答失败: {exc}") from exc

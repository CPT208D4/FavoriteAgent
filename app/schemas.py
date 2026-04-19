from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str
    title: str
    content: str
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DocumentCreate(BaseModel):
    id: Optional[str] = None
    title: str
    content: str
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    source_url: Optional[str] = None


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户问题或检索语句")
    top_k: int = Field(5, ge=1, le=50)


class ChunkHit(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    text: str
    distance: float = Field(
        ...,
        description="向量检索阶段距离，越小越相似；若启用 rerank，可与 rerank_score 一起看",
    )
    rerank_score: Optional[float] = Field(
        None, description="重排序模型给出的相关分，越高越相关（若未启用 rerank 则为 null）"
    )


class RetrieveResponse(BaseModel):
    query: str
    chunks: list[ChunkHit]


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户提问")
    top_k: int = Field(5, ge=1, le=20, description="检索片段数量")


class SourceItem(BaseModel):
    doc_id: str
    chunk_id: str
    title: str
    distance: float
    rerank_score: Optional[float] = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    used_fallback: bool = False


class ReportResponse(BaseModel):
    period: str
    doc_count: int
    report: str
    used_fallback: bool = Field(
        False,
        description="True 表示未调用成功 LLM，返回的是根据文档元数据自动拼出的摘要",
    )

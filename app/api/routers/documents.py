from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ...database import get_db
from ...schemas import Document, DocumentCreate, DocumentUpdate
from ...services import content_service

router = APIRouter(tags=["documents"])


@router.get("/documents", response_model=list[Document])
def list_documents(
    db: Session = Depends(get_db),
    category: str | None = Query(None, description="按分类筛选"),
    tag: str | None = Query(None, description="包含该标签"),
    q: str | None = Query(None, description="标题或正文关键词（简单包含匹配）"),
):
    return content_service.list_documents(db, category=category, tag=tag, q=q)


@router.get("/documents/{doc_id}", response_model=Document)
def get_one(doc_id: str, db: Session = Depends(get_db)):
    doc = content_service.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.post("/documents", response_model=Document)
def create(payload: DocumentCreate, db: Session = Depends(get_db)):
    return content_service.create_document(db, payload)


@router.post("/documents/upload", response_model=Document)
async def upload_document(
    file: UploadFile = File(..., description="支持 .txt/.md/.pdf/.docx"),
    title: str | None = Form(None, description="可选，不填则使用文件名"),
    category: str = Form("", description="可选分类"),
    tags: str = Form("", description="可选，逗号分隔：AI,RAG,学习"),
    source_url: str | None = Form(None, description="可选来源链接"),
    db: Session = Depends(get_db),
):
    try:
        raw = await file.read()
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        return content_service.create_document_from_upload(
            db,
            filename=file.filename or "uploaded.txt",
            raw=raw,
            title=title,
            category=category,
            tags=tag_list,
            source_url=source_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/documents/{doc_id}", response_model=Document)
def update(doc_id: str, payload: DocumentUpdate, db: Session = Depends(get_db)):
    doc = content_service.update_document(db, doc_id, payload)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.delete("/documents/{doc_id}")
def delete(doc_id: str, db: Session = Depends(get_db)):
    if not content_service.delete_document(db, doc_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"deleted": True, "id": doc_id}


@router.get("/export/rag-chunks")
def export_for_rag(db: Session = Depends(get_db)):
    """全量导出合并文本（调试用；正式检索请用 POST /retrieve）。"""
    return {"items": content_service.export_text_for_rag(db)}


@router.post("/admin/reindex-all")
def reindex_all(db: Session = Depends(get_db)):
    """文档已在库但向量异常时，可全量重建向量索引。"""
    n = content_service.rebuild_all_indexes(db)
    return {"reindexed_documents": n}

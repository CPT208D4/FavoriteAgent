import json
import uuid
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..config import settings
from ..db_models import Document as DocumentORM
from ..schemas import Document, DocumentCreate, DocumentUpdate
from . import chunking, embedding, vector_store


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _orm_to_schema(row: DocumentORM) -> Document:
    return Document.model_validate(row)


def _reindex_document(row: DocumentORM) -> None:
    vector_store.delete_by_doc_id(row.id)
    full_text = f"{row.title}\n\n{row.content}"
    chunks = chunking.split_into_chunks(
        full_text, settings.chunk_size, settings.chunk_overlap
    )
    if not chunks:
        return
    vectors = embedding.embed_texts(chunks)
    vector_store.add_document_chunks(row.id, row.title, chunks, vectors)


def list_documents(
    db: Session,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    q: Optional[str] = None,
) -> list[Document]:
    rows = db.query(DocumentORM).order_by(DocumentORM.created_at.desc()).all()
    out: list[Document] = []
    for row in rows:
        if category and row.category != category:
            continue
        if tag and tag not in (row.tags or []):
            continue
        if q:
            needle = q.lower()
            if needle not in row.title.lower() and needle not in row.content.lower():
                continue
        out.append(_orm_to_schema(row))
    return out


def get_document(db: Session, doc_id: str) -> Optional[Document]:
    row = db.get(DocumentORM, doc_id)
    if not row:
        return None
    return _orm_to_schema(row)


def create_document(db: Session, payload: DocumentCreate) -> Document:
    now = _utc_now()
    doc_id = payload.id or f"doc-{uuid.uuid4().hex[:12]}"
    created = payload.created_at or now
    row = DocumentORM(
        id=doc_id,
        title=payload.title,
        content=payload.content,
        category=payload.category or "",
        tags=payload.tags or [],
        source_url=payload.source_url,
        created_at=created,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _reindex_document(row)
    return _orm_to_schema(row)


def update_document(db: Session, doc_id: str, payload: DocumentUpdate) -> Optional[Document]:
    row = db.get(DocumentORM, doc_id)
    if not row:
        return None
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = _utc_now()
    db.commit()
    db.refresh(row)
    _reindex_document(row)
    return _orm_to_schema(row)


def delete_document(db: Session, doc_id: str) -> bool:
    row = db.get(DocumentORM, doc_id)
    if not row:
        return False
    vector_store.delete_by_doc_id(doc_id)
    db.delete(row)
    db.commit()
    return True


def export_text_for_rag(db: Session) -> list[dict]:
    rows = db.query(DocumentORM).order_by(DocumentORM.id).all()
    return [
        {"id": r.id, "title": r.title, "text": f"{r.title}\n\n{r.content}"}
        for r in rows
    ]


def seed_from_json_file(db: Session, path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for item in data:
        payload = DocumentCreate.model_validate(item)
        existing = db.get(DocumentORM, payload.id) if payload.id else None
        if existing:
            update_document(
                db,
                existing.id,
                DocumentUpdate(
                    title=payload.title,
                    content=payload.content,
                    category=payload.category,
                    tags=payload.tags,
                    source_url=payload.source_url,
                ),
            )
        else:
            create_document(db, payload)
        count += 1
    return count


def rebuild_all_indexes(db: Session) -> int:
    rows = db.query(DocumentORM).all()
    for row in rows:
        _reindex_document(row)
    return len(rows)


def _extract_text_from_upload(filename: str, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        return raw.decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    if suffix == ".docx":
        from docx import Document as DocxDocument

        doc = DocxDocument(BytesIO(raw))
        paras = [p.text for p in doc.paragraphs]
        return "\n".join(paras)
    raise ValueError("仅支持 .txt / .md / .pdf / .docx 文件")


def create_document_from_upload(
    db: Session,
    *,
    filename: str,
    raw: bytes,
    title: str | None = None,
    category: str = "",
    tags: list[str] | None = None,
    source_url: str | None = None,
) -> Document:
    text = _extract_text_from_upload(filename, raw).strip()
    if not text:
        raise ValueError("文件解析后为空，无法入库")
    final_title = (title or Path(filename).stem).strip() or "untitled"
    return create_document(
        db,
        DocumentCreate(
            title=final_title,
            content=text,
            category=category,
            tags=tags or [],
            source_url=source_url,
        ),
    )

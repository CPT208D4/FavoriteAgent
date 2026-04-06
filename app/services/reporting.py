from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..db_models import Document as DocumentORM
from . import llm


def _to_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _collect_docs(db: Session, days: int, max_docs: int) -> list[DocumentORM]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.query(DocumentORM).order_by(DocumentORM.created_at.desc()).all()
    out: list[DocumentORM] = []
    for r in rows:
        if _to_utc(r.created_at) >= cutoff:
            out.append(r)
        if len(out) >= max_docs:
            break
    return out


def _compose_context(rows: list[DocumentORM]) -> str:
    blocks: list[str] = []
    for r in rows:
        tags = ", ".join(r.tags or [])
        blocks.append(
            f"- 标题: {r.title}\n  分类: {r.category}\n  标签: {tags}\n  内容: {r.content}"
        )
    return "\n\n".join(blocks)


def generate_period_report(db: Session, days: int, max_docs: int) -> tuple[int, str]:
    rows = _collect_docs(db, days=days, max_docs=max_docs)
    if not rows:
        return 0, "本周期知识库暂无新增内容。"
    context = _compose_context(rows)
    system = (
        "你是学习知识库总结助手。请基于给定材料输出中文报告，格式固定：\n"
        "1) 本期主题概览（3-5条）\n"
        "2) 关键知识点（按主题分组）\n"
        "3) 可执行行动建议（3条）\n"
        "不要编造材料外信息。"
    )
    prompt = f"统计周期：最近 {days} 天\n\n材料：\n{context}"
    return len(rows), llm.chat_completion(system, prompt)

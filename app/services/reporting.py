import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..config import settings
from ..db_models import Document as DocumentORM
from . import llm

logger = logging.getLogger(__name__)


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


def _truncate(text: str, max_len: int) -> str:
    if max_len <= 0 or len(text) <= max_len:
        return text
    return text[: max_len - 30].rstrip() + "\n...(truncated)"


def _compose_context(rows: list[DocumentORM]) -> str:
    blocks: list[str] = []
    per = settings.report_max_chars_per_doc
    for r in rows:
        tags = ", ".join(r.tags or [])
        body = _truncate(r.content or "", per)
        blocks.append(
            f"- 标题: {r.title}\n  分类: {r.category}\n  标签: {tags}\n  内容: {body}"
        )
    joined = "\n\n".join(blocks)
    cap = settings.report_max_total_chars
    if len(joined) > cap:
        joined = joined[: cap - 80].rstrip() + "\n\n...(material truncated for weekly report)"
    return joined


def _preview(text: str, max_len: int = 280) -> str:
    t = (text or "").strip().replace("\r\n", "\n")
    if len(t) <= max_len:
        return t
    return t[: max_len - 20].rstrip() + "…"


def _fallback_report(rows: list[DocumentORM], err: BaseException) -> str:
    err_s = f"{type(err).__name__}: {err!s}"
    if len(err_s) > 400:
        err_s = err_s[:397] + "…"
    lines = [
        "[Weekly report — LLM unavailable] The model API did not return in time or "
        "returned an error. Below is an automatic outline from your documents.",
        "",
        f"Error (for debugging): {err_s}",
        "",
        f"Documents in this period ({len(rows)}):",
        "",
    ]
    for i, r in enumerate(rows, start=1):
        tags = ", ".join(r.tags or [])
        lines.append(
            f"{i}. **{r.title}** — category: {r.category}; tags: {tags}\n"
            f"   Preview: {_preview(r.content or '')}"
        )
    return "\n".join(lines)


def generate_period_report(db: Session, days: int, max_docs: int) -> tuple[int, str, bool]:
    rows = _collect_docs(db, days=days, max_docs=max_docs)
    if not rows:
        return 0, "本周期知识库暂无新增内容。", False
    context = _compose_context(rows)
    system = (
        "你是学习知识库周报助手。请仅基于给定材料输出一份自然、好读的英文周报。\n"
        "写作要求：\n"
        "1) 先概述本周主要主题，再提炼关键知识点与收获。\n"
        "2) 可以按主题分段，也可以用短列表，但不要机械套模板。\n"
        "3) 若材料里有数量或频次信息，可自然引用；没有就不要硬编数字。\n"
        "4) 结尾给出 2-3 条下周可执行建议。\n"
        "5) 严禁编造材料中不存在的事实。"
    )
    prompt = f"统计周期：最近 {days} 天\n\n材料：\n{context}"
    try:
        return len(rows), llm.chat_completion(system, prompt), False
    except Exception as exc:
        logger.warning("weekly report LLM failed: %s", exc, exc_info=True)
        return len(rows), _fallback_report(rows, exc), True

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..config import settings
from ..db_models import Document as DocumentORM
from . import llm

logger = logging.getLogger(__name__)


def _collect_docs(db: Session, days: int, max_docs: int) -> list[DocumentORM]:
    """Pick documents whose `created_at` falls within the last `days` days (UTC).

    Newest first, at most `max_docs` rows. Uses DB filter so we do not scan the whole table.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        db.query(DocumentORM)
        .filter(
            DocumentORM.created_at.isnot(None),
            DocumentORM.created_at >= cutoff,
        )
        .order_by(DocumentORM.created_at.desc())
        .limit(max_docs)
    )
    return list(q.all())


def _truncate(text: str, max_len: int) -> str:
    if max_len <= 0 or len(text) <= max_len:
        return text
    return text[: max_len - 30].rstrip() + "\n...(truncated)"


def _compose_context(rows: list[DocumentORM]) -> str:
    """Build prompt material with a **fair per-item budget** so many items in 7 days
    are all represented (avoids only the first long doc filling the token budget).
    """
    if not rows:
        return ""
    n = len(rows)
    cap = settings.report_max_total_chars
    # Headers per block (title, category, tags) — approximate character overhead.
    overhead_per = 200
    budget_for_bodies = max(400, cap - 500 - n * overhead_per)
    per = min(settings.report_max_chars_per_doc, budget_for_bodies // n)
    per = max(per, 200)

    blocks: list[str] = []
    for i, r in enumerate(rows, start=1):
        tags = ", ".join(r.tags or [])
        body = _truncate(r.content or "", per)
        blocks.append(
            f"[Item {i}/{n}] Title: {r.title}\n"
            f"  Category: {r.category}\n"
            f"  Tags: {tags}\n"
            f"  Content: {body}"
        )
    joined = "\n\n---\n\n".join(blocks)
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
        return 0, "No new knowledge-base documents were added in this period.", False
    context = _compose_context(rows)
    n = len(rows)
    system = (
        "You are a weekly report assistant for a favorites/knowledge-base app. "
        "Write the report in English only and use only the provided material.\n"
        "Requirements:\n"
        f"1) There are {n} distinct items in the material ([Item i/n]). Mention every item at least once. "
        "You may start with a short overview, then summarize each item briefly (title + one key point).\n"
        "2) Then extract cross-item themes or patterns if any.\n"
        "3) If numeric counts/frequencies exist in the material, you may cite them naturally; otherwise do not invent numbers.\n"
        "4) End with 2-3 actionable suggestions for next week.\n"
        "5) Do not fabricate facts not present in the material."
    )
    prompt = (
        f"Time window: last {days} days (items whose created_at is within this window).\n"
        f"Number of items included in this report: {n}.\n\n"
        f"Material:\n{context}"
    )
    try:
        return len(rows), llm.chat_completion(system, prompt), False
    except Exception as exc:
        logger.warning("weekly report LLM failed: %s", exc, exc_info=True)
        return len(rows), _fallback_report(rows, exc), True

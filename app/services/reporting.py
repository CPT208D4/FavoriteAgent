import logging
import re
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


def _clean_ui_sentence(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    # Remove common label-like prefixes that break UI cards.
    s = re.sub(
        r"^\s*(weekly report|summary|summary highlight|summary detail|highlight|detail|overview|item\s*\d+\s*/\s*\d+)\s*[:\-]\s*",
        "",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _sanitize_report_for_ui(report_text: str) -> str:
    text = (report_text or "").strip()
    if not text:
        return text
    normalized = re.sub(r"\s+", " ", text).strip()
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", normalized) if p.strip()]
    if not parts:
        return normalized

    first = _clean_ui_sentence(parts[0])
    second_source = parts[1] if len(parts) > 1 else parts[0]
    second = _clean_ui_sentence(second_source)
    first = first if re.search(r"[.!?]$", first) else first + "."
    second = second if re.search(r"[.!?]$", second) else second + "."

    remainder = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
    if remainder:
        return f"{first} {second} {remainder}".strip()
    return f"{first} {second}".strip()


def generate_period_report(db: Session, days: int, max_docs: int) -> tuple[int, str, bool]:
    rows = _collect_docs(db, days=days, max_docs=max_docs)
    if not rows:
        return 0, "No new knowledge-base documents were added in this period.", False
    context = _compose_context(rows)
    n = len(rows)
    system = (
        "You are a weekly report writer for a favorites/knowledge-base app. "
        "Write in English only and use only the provided material.\n"
        "Goal: produce concrete, informative output that is easy to display in compact UI cards.\n"
        "Output rules (must follow):\n"
        "1) Plain text only. Do NOT use Markdown syntax like **, #, -, bullets, or numbered lists.\n"
        "2) Total length: 180-320 words.\n"
        "3) The first TWO sentences are reserved for UI extraction:\n"
        "   - Sentence 1: one concise highlight sentence.\n"
        "   - Sentence 2: one concise detail sentence.\n"
        "   - These two sentences must be natural statements and must NOT contain labels like "
        "'Weekly Report', 'Summary', 'Highlight', 'Detail', 'Overview', 'Item 1/3', or a colon-based title.\n"
        "   - DO NOT start sentence 1 or sentence 2 with a heading word followed by ':' or '-'.\n"
        f"4) There are {n} distinct items in the material ([Item i/n]). Mention every item at least once in the remaining content.\n"
        "5) After the first two sentences, write 2 short paragraphs:\n"
        "   - Paragraph A: key evidence from the items.\n"
        "   - Paragraph B: cross-item patterns and 2 actionable next steps.\n"
        "6) Use specific facts/details from the material, avoid generic praise and filler.\n"
        "7) Use numbers only when present in material; do not invent numbers."
    )
    prompt = (
        f"Time window: last {days} days (items whose created_at is within this window).\n"
        f"Number of items included in this report: {n}.\n"
        "Important: the first two sentences will be shown separately in two UI cards, "
        "so keep both short, meaningful, and self-contained.\n\n"
        f"Material:\n{context}"
    )
    try:
        raw_report = llm.chat_completion(system, prompt)
        cleaned_report = _sanitize_report_for_ui(raw_report)
        return len(rows), cleaned_report, False
    except Exception as exc:
        logger.warning("weekly report LLM failed: %s", exc, exc_info=True)
        return len(rows), _fallback_report(rows, exc), True

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...config import settings
from ...database import get_db
from ...schemas import ReportResponse
from ...services.reporting import generate_period_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/weekly", response_model=ReportResponse)
def weekly_report(db: Session = Depends(get_db)):
    try:
        count, report, used_fallback = generate_period_report(
            db, days=7, max_docs=settings.report_max_docs
        )
        return ReportResponse(
            period="最近 7 天",
            doc_count=count,
            report=report,
            used_fallback=used_fallback,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"周报生成失败: {exc}") from exc

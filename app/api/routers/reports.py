from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...schemas import ReportRequest, ReportResponse
from ...services.reporting import generate_period_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportResponse)
def generate_report(body: ReportRequest, db: Session = Depends(get_db)):
    try:
        count, report = generate_period_report(db, body.days, body.max_docs)
        return ReportResponse(period=f"最近 {body.days} 天", doc_count=count, report=report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成报告失败: {exc}") from exc


@router.get("/daily", response_model=ReportResponse)
def daily_report(db: Session = Depends(get_db)):
    try:
        count, report = generate_period_report(db, days=1, max_docs=50)
        return ReportResponse(period="最近 1 天", doc_count=count, report=report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"日报生成失败: {exc}") from exc


@router.get("/weekly", response_model=ReportResponse)
def weekly_report(db: Session = Depends(get_db)):
    try:
        count, report = generate_period_report(db, days=7, max_docs=200)
        return ReportResponse(period="最近 7 天", doc_count=count, report=report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"周报生成失败: {exc}") from exc

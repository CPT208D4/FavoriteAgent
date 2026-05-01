from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...schemas import Theme, ThemeCreate
from ...services import themes_service

router = APIRouter(tags=["themes"])


@router.get("/themes", response_model=list[Theme])
def list_themes(db: Session = Depends(get_db)):
    return themes_service.list_themes(db)


@router.post("/themes", response_model=Theme)
def create_theme(payload: ThemeCreate, db: Session = Depends(get_db)):
    return themes_service.create_theme(db, payload)


@router.delete("/themes/{slug}")
def delete_theme(slug: str, db: Session = Depends(get_db)):
    if not themes_service.delete_theme(db, slug):
        raise HTTPException(status_code=404, detail="主题不存在")
    return {"deleted": True, "slug": slug}


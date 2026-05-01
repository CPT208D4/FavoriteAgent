from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..db_models import Theme as ThemeORM
from ..schemas import Theme, ThemeCreate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def list_themes(db: Session) -> list[ThemeORM]:
    return db.query(ThemeORM).order_by(ThemeORM.created_at.desc()).all()


def get_theme(db: Session, slug: str) -> ThemeORM | None:
    return db.get(ThemeORM, slug)


def create_theme(db: Session, payload: ThemeCreate) -> ThemeORM:
    existing = db.get(ThemeORM, payload.slug)
    if existing:
        existing.title = payload.title
        existing.description = payload.description
        existing.tags = payload.tags
        existing.updated_at = _utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    row = ThemeORM(
        slug=payload.slug,
        title=payload.title,
        description=payload.description,
        tags=payload.tags,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_theme(db: Session, slug: str) -> bool:
    row = db.get(ThemeORM, slug)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


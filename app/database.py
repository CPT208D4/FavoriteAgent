from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import settings

# Ensure local sqlite target directories exist before engine opens files.
if settings.data_dir:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
if settings.chroma_dir:
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)

connect_args = {}
if settings.database_url and settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url or "",
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    from . import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

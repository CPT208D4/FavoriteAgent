from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import settings


def _ensure_writable_dirs() -> None:
    # Vercel project path (/var/task) is read-only. If path resolution misses,
    # fallback here to /tmp to keep startup alive.
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        if exc.errno != 30:  # Read-only file system
            raise
        settings.data_dir = Path("/tmp/knowledgebase-data")
        settings.chroma_dir = settings.data_dir / "chroma"
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        settings.database_url = f"sqlite:///{settings.data_dir / 'kb.sqlite'}"


_ensure_writable_dirs()

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

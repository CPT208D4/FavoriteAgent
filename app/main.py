from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routers import chat_router, documents_router, reports_router, retrieval_router
from .database import SessionLocal, init_db
from .db_models import Document as DocumentORM
from .services.content_service import seed_from_json_file


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    # Seed bundled documents on empty database only.
    db = SessionLocal()
    try:
        has_data = db.query(DocumentORM.id).first() is not None
        if not has_data:
            seed_path = Path(__file__).resolve().parent.parent / "data" / "documents.json"
            if seed_path.exists():
                seed_from_json_file(db, seed_path)
    finally:
        db.close()
    yield


app = FastAPI(
    title="知识库 API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(retrieval_router)
app.include_router(chat_router)
app.include_router(reports_router)

# Keep legacy routes and also expose /api/* for one-project deployments.
api_prefixed_router = APIRouter(prefix="/api")
api_prefixed_router.include_router(documents_router)
api_prefixed_router.include_router(retrieval_router)
api_prefixed_router.include_router(chat_router)
api_prefixed_router.include_router(reports_router)
app.include_router(api_prefixed_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}

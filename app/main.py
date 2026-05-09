# Import async context manager decorator for managing application startup/shutdown lifecycle
from contextlib import asynccontextmanager
from pathlib import Path

# Import core FastAPI framework components
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all feature route modules from the internal api package
# Import all feature route modules from the internal api package
from .api.routers import (
    chat_router,
    documents_router,
    reports_router,
    retrieval_router,
    themes_router,
)
# Import database session factory and database initialization utility
from .database import SessionLocal, init_db
# Import Document ORM model, aliased as DocumentORM to avoid naming conflicts with service layer models
from .db_models import Document as DocumentORM
# Import utility function to seed initial document data from a JSON file
from .services.content_service import seed_from_json_file


# Define application lifespan context manager to run startup/shutdown logic
@asynccontextmanager
async def lifespan(_: FastAPI):
    # Initialize database tables and schema on application startup
    init_db()
    # Create a temporary database session for data seeding operations
    db = SessionLocal()
    try:
        # Check if the documents table already has existing records to avoid duplicate seeding
        has_data = db.query(DocumentORM.id).first() is not None
        # Only run seeding logic if the database is empty
        if not has_data:
            # Construct absolute path to the bundled seed documents JSON file (located in project root /data directory)
            seed_path = Path(__file__).resolve().parent.parent / "data" / "documents.json"
            # Verify the seed file exists before attempting to read it
            if seed_path.exists():
                # Populate the database with initial document data from the JSON seed file
                seed_from_json_file(db, seed_path)
    finally:
        # Close the database session to release resources regardless of seeding success/failure
        db.close()
    # Yield control to the running FastAPI application for its entire lifetime
    yield


# Create the core FastAPI application instance
app = FastAPI(
    title="Knowledge Base API",  # Human-readable title displayed in auto-generated OpenAPI docs
    version="0.2.0",  # Current API version for version tracking and client compatibility checks
    lifespan=lifespan,  # Attach custom lifecycle manager to handle startup/shutdown tasks
)

# Add CORS middleware to the application middleware stack
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from all origins (restrict to specific domains in production for security)
    allow_credentials=True,  # Allow cross-origin requests to send credentials (cookies, auth headers)
    allow_methods=["*"],  # Allow all standard HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all request headers from client applications
)

# Route registration
# Register feature routers at their default base prefixes
app.include_router(documents_router)
app.include_router(themes_router)
app.include_router(retrieval_router)
app.include_router(chat_router)
app.include_router(reports_router)

# Create secondary router group with /api prefix to support both legacy routes and /api/* paths for single-project deployments
api_prefixed_router = APIRouter(prefix="/api")
# Mount all feature routers under the /api prefix
api_prefixed_router.include_router(documents_router)
api_prefixed_router.include_router(themes_router)
api_prefixed_router.include_router(retrieval_router)
api_prefixed_router.include_router(chat_router)
api_prefixed_router.include_router(reports_router)
# Register the prefixed router group with the main application
app.include_router(api_prefixed_router)


# Public unprefixed health check endpoint for load balancers and monitoring tools
@app.get("/health")
def health():
    # Return simple status payload to indicate the service is running normally
    return {"status": "ok"}


# Prefixed health check endpoint to match the /api/* routing pattern
@app.get("/api/health")
def api_health():
    # Return simple status payload for the prefixed health check route
    return {"status": "ok"}

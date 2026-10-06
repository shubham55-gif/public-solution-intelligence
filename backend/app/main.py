"""FastAPI application entry point for Public Solution Intelligence."""

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import UPLOADS_DIR
from app.db.database import is_database_connected


UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Public Solution Intelligence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.include_router(api_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    """Verify that both the API process and PostgreSQL are available."""
    if not is_database_connected():
        raise HTTPException(status_code=503, detail="Database unavailable")

    return {
        "status": "ok",
        "service": "public-solution-intelligence",
        "database": "connected",
    }

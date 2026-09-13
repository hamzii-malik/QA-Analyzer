from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routes.analysis import router as analysis_router
from app.routes.upload import router as upload_router


reports_dir = Path(__file__).resolve().parents[1] / "reports"
reports_dir.mkdir(parents=True, exist_ok=True)
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI-powered QA Analyzer",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "version": "1.0.0",
    }


app.include_router(analysis_router)
app.include_router(upload_router)

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
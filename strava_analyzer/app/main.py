import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from strava_analyzer.app.routes.webhook import router as webhook_router
from strava_analyzer.app.routes.activities import router as activities_router
from strava_analyzer.app.routes.auth import router as auth_router
from strava_analyzer.app.routes.login import router as login_router

from dotenv import load_dotenv

load_dotenv()

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="Strava Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://strava.bngrd.com",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login_router)
app.include_router(webhook_router)
app.include_router(activities_router)
app.include_router(auth_router)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def root():
    """Serve frontend index.html."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy"}

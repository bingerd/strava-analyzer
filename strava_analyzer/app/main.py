from fastapi import FastAPI
from strava_analyzer.app.routes.webhook import router as webhook_router
from strava_analyzer.app.routes.activities import router as activities_router
from strava_analyzer.app.routes.auth import router as auth_router

app = FastAPI(title="Strava Analyzer API")

app.include_router(webhook_router)
app.include_router(activities_router)
app.include_router(auth_router)

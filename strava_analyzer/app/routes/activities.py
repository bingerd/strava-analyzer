from fastapi import APIRouter, HTTPException
from typing import List
from strava_analyzer.app.models.activity import Activity
from strava_analyzer.app.services.strava import get_all_activities, get_activity

router = APIRouter(prefix="/activities", tags=["activities"])

@router.get("/", response_model=List[Activity])
def fetch_all_activities():
    try:
        data = get_all_activities()
        return [Activity(**a) for a in data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{activity_id}", response_model=Activity)
def fetch_activity(activity_id: int):
    try:
        data = get_activity(activity_id)
        return Activity(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

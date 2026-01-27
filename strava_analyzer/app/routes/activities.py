from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List
from strava_analyzer.app.models.activity import Activity
from strava_analyzer.app.services.strava import get_all_activities_for_user, get_activity_for_user
from strava_analyzer.app.services.users import get_user_tokens
from strava_analyzer.app.services.security import get_current_user

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("/", response_model=List[Activity])
def fetch_all_activities(
    athlete_id: int = Query(..., description="Strava athlete ID"),
    current_user: str = Depends(get_current_user),
):
    """
    Fetch all activities for a specific athlete.
    Requires authentication.
    """
    tokens = get_user_tokens(athlete_id)
    if tokens is None:
        raise HTTPException(
            status_code=404,
            detail=f"Athlete {athlete_id} not found. Please authorize first at /auth/authorize"
        )

    try:
        data = get_all_activities_for_user(athlete_id)
        return [Activity(**a) for a in data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{activity_id}", response_model=Activity)
def fetch_activity(
    activity_id: int,
    athlete_id: int = Query(..., description="Strava athlete ID"),
    _: str = Depends(get_current_user),
):
    """
    Fetch a specific activity for an athlete.
    Requires authentication.
    """
    tokens = get_user_tokens(athlete_id)
    if tokens is None:
        raise HTTPException(
            status_code=404,
            detail=f"Athlete {athlete_id} not found. Please authorize first at /auth/authorize"
        )

    try:
        data = get_activity_for_user(athlete_id, activity_id)
        return Activity(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel
from typing import Optional, List

class Activity(BaseModel):
    id: int
    name: str
    distance: float
    moving_time: int
    elapsed_time: int
    total_elevation_gain: float
    type: str
    start_date: str
    average_speed: Optional[float]
    max_speed: Optional[float]

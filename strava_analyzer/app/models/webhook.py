from pydantic import BaseModel
from typing import Optional, Dict


class WebhookEvent(BaseModel):
    aspect_type: str
    event_time: int
    object_id: int
    object_type: str
    owner_id: int
    subscription_id: int
    updates: Optional[Dict] = None

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models import Listing

class ListingOut(Listing):
    model_config = ConfigDict(from_attributes=True)
    first_seen: datetime
    last_seen: datetime

class ListingPage(BaseModel):
    items: list[ListingOut]
    total: int
    limit: int
    offset: int
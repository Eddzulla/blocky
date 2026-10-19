from typing import Annotated, Literal
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import ListingOut, ListingPage
from app.db import crud, models as db

router = APIRouter(prefix="/listings", tags=["listings"])
SessionDep = Annotated[Session, Depends(get_db)]

@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, session: SessionDep):
    listing = session.get(db.Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code = 404, detail="Listing not found")
    return listing

@router.get("", response_model=ListingPage)
def get_listings(
        session: SessionDep,
        vertical: Literal["car", "mc"],
        price_min: Annotated[int | None, Query(ge=0)] = None,
        price_max: Annotated[int | None, Query(ge=0)] = None,
        make: str | None = None,
        location: str | None = None,
        sort: Literal["price", "year", "mileage", "last_seen"] = "last_seen",
        order: Literal["asc", "desc"] = "desc",
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = None
):
    items, total = crud.get_listings(
        session, vertical=vertical, price_min=price_min, price_max=price_max,
        make=make, location=location, sort=sort, order=order,
        limit=limit, offset=offset,
    )
    return ListingPage(
        items=[ListingOut.model_validate(i) for i in items],
        total=total, limit=limit, offset=offset,
    )
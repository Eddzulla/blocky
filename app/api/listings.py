from typing import Annotated, Literal
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import ListingOut, ListingPage
from app.db import crud, models as db

router = APIRouter(prefix="/listings", tags=["listings"])
SessionDep = Annotated[Session, Depends(get_db)]

@router.get("/makes", response_model=list[str])
def get_makes(session: SessionDep, vertical: Literal["car", "mc"]):
    return crud.get_makes(session, vertical=vertical)

@router.get("/models", response_model=list[str])
def get_models(
    session: SessionDep,
    vertical: Literal["car", "mc"],
    make: Annotated[list[str] | None, Query()] = None,
):
    return crud.get_models(session, vertical=vertical, make=make)

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
        mileage_min: Annotated[int | None, Query(ge=0)] = None,
        mileage_max: Annotated[int | None, Query(ge=0)] = None,
        make: Annotated[list[str] | None, Query()] = None,
        model: Annotated[list[str] | None, Query()] = None,
        search: str | None = None,
        location: str | None = None,
        year_min: Annotated[int | None, Query(ge=1900)] = None,
        year_max: Annotated[int | None, Query(ge=1900)] = None,
        sort: Literal["price", "year", "mileage", "make", "model", "engine_cc", "last_seen"] = "last_seen",
        order: Literal["asc", "desc"] = "desc",
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0
):
    items, total = crud.get_listings(
        session, vertical=vertical, price_min=price_min, price_max=price_max,
        mileage_min=mileage_min, mileage_max=mileage_max,
        make=make, model=model, search=search, location=location, year_min=year_min, year_max=year_max,
        sort=sort, order=order, limit=limit, offset=offset,
    )
    return ListingPage(
        items=[ListingOut.model_validate(i) for i in items],
        total=total, limit=limit, offset=offset,
    )
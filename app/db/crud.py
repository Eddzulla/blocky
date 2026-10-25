from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import models as db
from app.models import Listing

def upsert_listings(session: Session, listings: list[Listing]) -> None:
    if not listings:
        return 

    rows = [listing.model_dump() for listing in listings]

    stmt = insert(db.Listing).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[db.Listing.id],
        set_={
            **{col: stmt.excluded[col] for col in rows[0] if col != "id"},
            "last_seen": func.now(),
        },
    )
    session.execute(stmt)

def get_listings(
    session: Session,
    *,
    vertical: str,
    price_min: int | None,
    price_max: int | None,
    make: list[str] | None,
    location: str | None,
    year_min: int | None,
    year_max: int | None,
    sort: str,
    order: str,
    limit: int,
    offset: int,
) -> tuple[list[db.Listing], int]:
    query = select(db.Listing).where(db.Listing.vertical == vertical)

    if price_min is not None:
        query = query.where(db.Listing.price_sek >= price_min)
    if price_max is not None:
        query = query.where(db.Listing.price_sek <= price_max)
    if make:
        query = query.where(func.lower(db.Listing.make).in_([m.lower() for m in make]))
    if location is not None:
        query = query.where(db.Listing.location == location)
    if year_min is not None:
        query = query.where(db.Listing.year >= year_min)
    if year_max is not None:
        query = query.where(db.Listing.year <= year_max)

    total = session.scalar(select(func.count()).select_from(query.subquery()))
    
    sort_column = {
        "price": db.Listing.price_sek,
        "year": db.Listing.year,
        "mileage": db.Listing.mileage_km,
        "last_seen": db.Listing.last_seen,
    }[sort]
    sort_column = sort_column.desc().nulls_last() if order == "desc" else sort_column.asc().nulls_last()
    
    items = session.scalars(
        query.order_by(sort_column).limit(limit).offset(offset)
    ).all()
    return items, total

def get_makes(session: Session, *, vertical: str) -> list[str]:
    lowered = func.lower(db.Listing.make)
    return list(session.scalars(
        select(lowered)
        .where(db.Listing.vertical == vertical)
        .distinct()
        .order_by(lowered)
    ).all())

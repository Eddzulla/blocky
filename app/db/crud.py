from sqlalchemy import func, or_, select, update
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
            "is_active": True,
        },
    )
    session.execute(stmt)

def get_existing_ids(session: Session, *, vertical: str) -> set[int]:
    '''All ids ever stored for this vertical, active or not — used by the quick-fetch to
    know where to stop paging through newest-first results.'''
    return set(session.scalars(
        select(db.Listing.id).where(db.Listing.vertical == vertical)
    ).all())

def deactivate_missing(session: Session, *, vertical: str, active_ids: list[int]) -> int:
    '''Mark listings of this vertical as inactive if they weren't in the current fetch.
    Guards against wiping everything out if active_ids is empty (e.g. a failed fetch).'''
    if not active_ids:
        return 0

    stmt = (
        update(db.Listing)
        .where(
            db.Listing.vertical == vertical,
            db.Listing.is_active.is_(True),
            db.Listing.id.not_in(active_ids),
        )
        .values(is_active=False)
    )
    result = session.execute(stmt)
    return result.rowcount

def get_listings(
    session: Session,
    *,
    vertical: str,
    price_min: int | None,
    price_max: int | None,
    mileage_min: int | None,
    mileage_max: int | None,
    make: list[str] | None,
    model: list[str] | None,
    search: str | None,
    location: str | None,
    year_min: int | None,
    year_max: int | None,
    sort: str,
    order: str,
    limit: int,
    offset: int,
) -> tuple[list[db.Listing], int]:
    query = select(db.Listing).where(
        db.Listing.vertical == vertical,
        db.Listing.is_active.is_(True),
    )

    if price_min is not None:
        query = query.where(db.Listing.price_sek >= price_min)
    if price_max is not None:
        query = query.where(db.Listing.price_sek <= price_max)
    if mileage_min is not None:
        query = query.where(db.Listing.mileage_km >= mileage_min)
    if mileage_max is not None:
        query = query.where(db.Listing.mileage_km <= mileage_max)
    if make:
        query = query.where(func.lower(db.Listing.make).in_([m.lower() for m in make]))
    if model:
        query = query.where(func.lower(db.Listing.model).in_([m.lower() for m in model]))
    if search:
        for word in search.lower().split():
            query = query.where(
                or_(
                    func.lower(db.Listing.make).contains(word),
                    func.lower(db.Listing.model).contains(word),
                )
            )
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
        "make": db.Listing.make,
        "model": db.Listing.model,
        "engine_cc": db.Listing.engine_cc,
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
        .where(db.Listing.vertical == vertical, db.Listing.is_active.is_(True))
        .distinct()
        .order_by(lowered)
    ).all())

def get_models(session: Session, *, vertical: str, make: list[str] | None = None) -> list[str]:
    lowered = func.lower(db.Listing.model)
    query = (
        select(lowered)
        .where(
            db.Listing.vertical == vertical,
            db.Listing.is_active.is_(True),
            db.Listing.model.is_not(None),
        )
    )
    if make:
        query = query.where(func.lower(db.Listing.make).in_([m.lower() for m in make]))
    return list(session.scalars(query.distinct().order_by(lowered)).all())

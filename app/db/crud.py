from sqlalchemy import func
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

def get_lisitngs():
    pass
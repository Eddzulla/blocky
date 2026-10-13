from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

class Listing(Base):
    __tablename__= "listings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    vertical: Mapped[str] = mapped_column(index=True)
    url: Mapped[str]
    location: Mapped[str]
    price_sek: Mapped[int | None]
    year: Mapped[int]
    mileage_km: Mapped[int | None]
    make: Mapped[str]
    model: Mapped[str | None]
    model_specification: Mapped[str | None]
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

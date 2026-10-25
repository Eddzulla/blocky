from datetime import datetime

from sqlalchemy import ARRAY, BigInteger, DateTime, ForeignKey, String, func
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
    image_urls: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    engine_cc: Mapped[int | None]
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", index=True)

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.api import listings
from app.api.deps import get_db
from app.db.base import check_db

app = FastAPI(title="blocky")

app.include_router(listings.router)

@app.get("/health")
def health(session: Session = Depends(get_db)):
    if not check_db():
        return {"status": "ok", "db": "NOT OK"}
    return {"status": "ok", "db": "ok"}




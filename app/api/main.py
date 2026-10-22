from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.api import listings
from app.api.deps import get_db
from app.db.base import check_db
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="blocky")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(listings.router)

@app.get("/health")
def health(session: Session = Depends(get_db)):
    if not check_db():
        return JSONResponse(status_code=503, content={"status": "error", "db": "unreachable"})  
    return JSONResponse(status_code=200, content={"status": "ok", "db": "ok"})




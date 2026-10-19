from fastapi import FastAPI
from app.api import listings
app = FastAPI(title="blocky")

app.include_router(listings.router)

@app.get("/health")
def health():
    return {"status": "ok"}




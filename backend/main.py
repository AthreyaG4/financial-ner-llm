from fastapi import FastAPI

from db import init_db
from routes.extractions import router as extractions_router
from routes.health import router as health_router

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(extractions_router)
app.include_router(health_router)

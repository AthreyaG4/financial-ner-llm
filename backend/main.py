from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import init_db
from routes.extractions import router as extractions_router
from routes.health import router as health_router

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(extractions_router)
app.include_router(health_router)

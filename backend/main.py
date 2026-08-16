from fastapi import FastAPI
from database import engine, get_db
import models

# Create all database tables
models.Base.metadata.create_all(bind=engine)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Value Chain AI Opportunity Intelligence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import router
app.include_router(router)

@app.get("/")
def read_root():
    return {"status": "ok"}

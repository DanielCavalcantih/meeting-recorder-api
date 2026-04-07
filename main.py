from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from database import engine
from models import Base
from routers import recorder, billing

app = FastAPI()
site_url = os.getenv("SITE_URL")    

origins = [
    site_url
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(recorder.router)
app.include_router(billing.router)


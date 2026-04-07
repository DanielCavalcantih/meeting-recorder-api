from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from routers import recorder, billing

app = FastAPI()
site_url = os.getenv("SITE_URL")    

origins = [site_url] if site_url else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recorder.router)
app.include_router(billing.router)


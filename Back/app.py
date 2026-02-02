from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Routers
from Back.routers import login, upload

from typing import List
import numpy as np
import cv2

from PIL import Image
import pillow_heif

# Modules
from Back.core.pipeline import load_models
from Back.db.database import create_db_and_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
  
  # 1- Load all models (yolo + ocr)
  hunter, surgeon, reader = await load_models()
  
  app.state.hunter_model = hunter
  app.state.surgeon_model = surgeon
  app.state.reader = reader
  
  # 2- create db
  await create_db_and_tables()

  yield

app = FastAPI(lifespan=lifespan)

origins = [
  "http://localhost:5173" # for local testing (yes i will add the frontend url when i host it)
]

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
  expose_headers=["Content-Disposition"]
)

# connecting routers
app.include_router(login.router)
app.include_router(upload.router)
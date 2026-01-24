import cv2
from fastapi import FastAPI, HTTPException, UploadFile, File
from contextlib import asynccontextmanager

import numpy as np
# Modules
from Back.pipeline import load_models, process_sheet, save_data

@asynccontextmanager
async def lifespan(app: FastAPI):
  hunter, surgeon, reader = await load_models()

  app.state.hunter_model = hunter
  app.state.surgeon_model = surgeon
  app.state.reader = reader

  yield

app = FastAPI(lifespan=lifespan)

@app.post("/upload")
async def upload_sheet(
        image: UploadFile = File(...)
):
  """
  """

  ALLOWED_TYPES = ["image/jpeg", "image/png", "image/jpg"]

  if image.content_type not in ALLOWED_TYPES:
    raise HTTPException(status_code=400,
                        detail="Invalid file type. Only JPEG, PNG, and WEBP images are allowed.")

  # have to convert image to numpy array or it will give an error
  contents = await image.read() # filee bytes
  np_array = np.frombuffer(contents, np.uint8) # converts the bytes to numpy array
  image_array = cv2.imdecode(np_array, cv2.IMREAD_COLOR) # decode back into openCv

  if image_array is None:
    raise HTTPException(status_code=400, detail="Could not decode image")

  hunter = app.state.hunter_model
  surgeon = app.state.surgeon_model
  reader = app.state.reader

  result = process_sheet(image=image_array,
                         hunter=hunter,
                         surgeon=surgeon,
                         reader=reader,
                         filename=image.filename)

  if result:
    return save_data(result)

  else:
    raise HTTPException(status_code=500, detail="Couldn't process the image")
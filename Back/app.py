from fastapi import FastAPI, HTTPException, UploadFile, File
from contextlib import asynccontextmanager
from typing import List
import numpy as np
import cv2

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

MAX_IMAGES = 5
@app.post("/upload")
async def upload_sheet(
        images: List[UploadFile] = File(...)
):
  """
  1- Load models from state
  2- Check if provided images do not exceed the maximum number allowed
  3- Check if image is allowed
  4- Process each image and store all data
  5- Save data
  """

  if len(images) > MAX_IMAGES:
    raise HTTPException(status_code=422, detail=f"Maximum of {MAX_IMAGES} images is allowed!")

  ALLOWED_TYPES = ["image/jpeg", "image/png", "image/jpg"]

  all_patient_data = []

  hunter = app.state.hunter_model
  surgeon = app.state.surgeon_model
  reader = app.state.reader

  for image in images:

    if image.content_type not in ALLOWED_TYPES:
      # skip instead of crashing everything
      print(f"Skipping {image.filename}: Invalid type {image.content_type}")
      continue

    # read and decode
    # have to convert image to numpy array or it will give an error
    contents = await image.read() # filee bytes
    np_array = np.frombuffer(contents, np.uint8) # converts the bytes to numpy array
    image_array = cv2.imdecode(np_array, cv2.IMREAD_COLOR) # decode back into openCv

    if image_array is None:
      print(f"Skipping {image.filename}: Could not decode the image")
      continue

    try:
      sheet_result = process_sheet(
        image=image_array,
        hunter=hunter,
        surgeon=surgeon,
        reader=reader,
        filename=image.filename
      )

      all_patient_data.extend(sheet_result)

    except Exception as e:
      print(f"Error while processing {image.filename}: {e}")
      continue

  if all_patient_data:
    return save_data(all_patient_data)

  else:
    raise HTTPException(status_code=500, detail="No patients found in any of the uploaded images")
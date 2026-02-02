from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from typing import List
import numpy as np
import cv2

from PIL import Image
import pillow_heif

# Modules
from Back.core.pipeline import load_models, process_sheet, save_data
from Back.db.models import User
from Back.db.database import get_db
from Back.dependencies import get_current_user, oauth2_scheme

router = APIRouter(
  tags=["Upload"]
)

MAX_IMAGES = 5
@router.post("/upload")
async def upload_sheet(
        request: Request,
        user: User = Depends(get_current_user),
        images: List[UploadFile] = File(...)
):
  """
  1- Check if the user is active (by the get_current_user)
  2- Load models from state
  3- Check if provided images do not exceed the maximum number allowed
  4- Check if image is allowed
  5- Process each image and store all data (Read and Decode)
  6- Save data
  """


  if len(images) > MAX_IMAGES:
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Maximum of {MAX_IMAGES} images is allowed!")
  
  ALLOWED_TYPES = ["image/jpeg", "image/png", "image/jpg", "image/dng", "image/heic", "image/heif"]
  
  all_patient_data = []
  
  hunter = request.app.state.hunter_model
  surgeon = request.app.state.surgeon_model
  reader = request.app.state.reader
  
  for image in images:
    
    if image.content_type not in ALLOWED_TYPES and not image.filename.lower().endswith(('.heic', '.heif')):
      # skip instead of crashing everything
      print(f"Skipping {image.filename}: Invalid type {image.content_type}")
      continue
    
    # read and decode
    contents = await image.read()
    image_array = None
    
    try:
      is_heic = (
              image.content_type in ["image/heic", "image/heif"] or
              image.filename.lower().endswith(('.heic', '.heif'))
      )
      
      if is_heic:
        print(f"Processing HEIC/HEIF file: {image.filename}")
        heif_file = pillow_heif.read_heif(contents)
        
        # converts the heif image to a PIL image
        pil_image = Image.frombytes(
          heif_file.mode,
          heif_file.size,
          heif_file.data,
          "raw",
        )
        
        # convert PIL image (RGB) to opencv (BGR)
        np_image = np.array(pil_image)
        image_array = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
      
      else:
        # normal images processing
        np_array = np.frombuffer(contents, np.uint8)
        image_array = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    
    except Exception as e:
      print(f"Failed to decode image {image.filename}, Error: {e}")
      continue
    
    # process the image array
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
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No patients found in any of the uploaded images")
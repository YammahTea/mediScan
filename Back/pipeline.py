from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from ultralytics import YOLO
import easyocr

from io import BytesIO
import pandas as pd
import cv2


# Modules
from Back.ocr import get_best_ocr, clean_age, clean_text

HUNTER_MODEL_PATH = './models/detect/train1/weights/best.pt'
SURGEON_MODEL_PATH = './models/surgeon/train_v1/weights/best.pt'
OCR_CONFIDENCE_THRESHOLD = 0.3

async def load_models():
  print("Loading hunter model...")
  hunter = YOLO(HUNTER_MODEL_PATH)

  print("Loading surgeon model...")
  surgeon = YOLO(SURGEON_MODEL_PATH)

  print("Loading OCR model...")
  reader = easyocr.Reader(['en', 'ar'], gpu=True)

  return hunter, surgeon, reader


def process_sheet(image, hunter, surgeon, reader):
  final_data = []
  sheet = image

  hunter_results= hunter(sheet, verbose=False)
  if len(hunter_results[0].boxes) == 0:
    raise HTTPException(status_code=502, detail="Couldn't find any stickers")

  for _, sticker_box in enumerate(hunter_results[0].boxes):

    hospital_id = int(sticker_box.cls[0])
    hospital_name = hunter.names[hospital_id]

    x1, y1, x2, y2 = map(int, sticker_box.xyxy[0])
    sticker_crop = sheet[y1:y2, x1:x2]

    if sticker_crop.size == 0:
      continue

    surgeon_result = surgeon(sticker_crop, verbose=False)

    patient_info = {
      "File Name": "Not implemented yet",
      "Sticker image": "Not implemented yet",
      "Hospital Name": hospital_name,
      "Name": "-",
      "Entrance Date": "-",
      "Age": "-",
      "Payment": "-"
    }

    names_map = surgeon.names

    for box in surgeon_result[0].boxes:
      class_id = int(box.cls[0])
      class_name = names_map[class_id]

      bx1, by1, bx2, by2 = map(int, box.xyxy[0])
      field_cropped = sticker_crop[by1:by2, bx1:bx2]

      text, confidence = get_best_ocr(reader, field_cropped)

      if confidence < OCR_CONFIDENCE_THRESHOLD:
        final_value = "-"
      else:
        final_value = clean_text(text)

      if class_name == "field_name":
        patient_info["Name"] = final_value
      elif class_name == "field_date":
        patient_info["Entrance Date"] = final_value
      elif class_name == "field_age":
        patient_info["Age"] = clean_age(final_value)
      elif class_name == "field_payment":
        patient_info["Payment"] = final_value

    final_data.append(patient_info)

  return final_data



def save_data(patient_data):

  if not patient_data:
    raise HTTPException(status_code=502, detail="Couldn't extract data from stickers")

  df = pd.DataFrame(patient_data)
  cols = ["File Name", "Sticker image", "Hospital Name", "Name", "Entrance Date", "Age", "Payment"]
  cols = [c for c in cols if c in df.columns]
  df = df[cols]

  # in memory buffer
  buffer = BytesIO()
  df.to_excel(buffer, index=False, engine='openpyxl')
  buffer.seek(0)

  return StreamingResponse(
    buffer,
    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    headers={"Content-Disposition": "attachment; filename=patient_data.xlsx"}
  )
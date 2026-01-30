from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from ultralytics import YOLO
import easyocr

from datetime import datetime
from io import BytesIO
import pandas as pd
import cv2
import xlsxwriter


# Modules
from Back.ocr import *

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

hospital_map = {
  "amman": "مستشفى عمان الجراحي",
  "hayaa": "مستشفى الحياة",
  "almqased": "مستشفى المقاصد",
  "hanan": "مستشفى الحنان",
  "other": "Other"
}

def process_sheet(image, hunter, surgeon, reader, filename):
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

    if sticker_box.conf[0] <= 0.3: # to handle low confidence predictions
      hospital_name = "other"

    # Save cropped sticker
    # convert the numpy array into PNG formatted byte string
    success, encoded_image = cv2.imencode('.png', sticker_crop)
    sticker_bytes = encoded_image.tobytes() if success else None

    # case to handle the 'other' class by saving it as ghost patient but only saving the sticker image part
    if hospital_name == "other":
      print(f"Found 'other' sticker in {filename}, skipping surgeon model")
      patient_info = {
        "المريض": "-",
        "تاريخ الدخول": "-",
        "تاريخ الخروج": "-",
        "ملاحظات": "-",
        "Age": "-",
        "المستشفى": hospital_map.get(hospital_name, "Other"),
        "Payment": "-", # example: cash or insurance company
        "diagnosis": "-",
        "Expected Payment": "-", # expected amount to receive
        "Sticker image": "Manual Check Required", # just a placeholder text
        "File Name": filename,
        "image_data": sticker_bytes,
      }

      final_data.append(patient_info)
      continue

    surgeon_result = surgeon(sticker_crop, verbose=False)

    # this is temp, used to convert the image_data into an image
    patient_info = {
      "المريض": "-",
      "تاريخ الدخول": "-",
      "تاريخ الخروج": "-",
      "ملاحظات": "-",
      "Age": "-",
      "المستشفى": hospital_map.get(hospital_name, "Other"),
      "Payment": "-", # example: cash or insurance company
      "diagnosis": "-",
      "Expected Payment": "-", # expected amount to receive
      "Sticker image": "Not available",
      "File Name": filename,
      "image_data": sticker_bytes
    }

    names_map = surgeon.names

    # special case check
    if hospital_name == "amman":
      detected_classes = [names_map[int(box.cls[0])] for box in surgeon_result[0].boxes]
      if "field_payment" not in detected_classes:
        patient_info["Payment"] = "Cash"

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
        # the ocr model sometimes confuses the name field by saying "nathealth" instead, it's an insurance, not a name
        if "nathealth" in final_value.lower() or "nat" in final_value.lower():
          continue

        patient_info["المريض"] = final_value

      elif class_name == "field_date":
        patient_info["تاريخ الدخول"] = standardize_date(final_value)

      elif class_name == "field_age":
        patient_info["Age"] = clean_age(final_value)

      elif class_name == "field_payment":
        patient_info["Payment"] = clean_payment(final_value)

    final_data.append(patient_info)

  return final_data



def save_data(patient_data):
  """
  1- Convert the received dict into dataframe
  2- Create temp df based off the defined excel structure
  3- Write patient data into an excel sheet
  4- Insert images into the created excel sheet
  """
  if not patient_data:
    raise HTTPException(status_code=502, detail="Couldn't extract data from stickers")

  # 1- create df
  df = pd.DataFrame(patient_data)

  # 2- temp df for writing text (without the "image_data")
  # excel sheet configuration
  # format: ("Column name", column_width)

  excel_structure = [
    ("المريض", 30),
    ("تاريخ الدخول", 15),
    ("تاريخ الخروج", 15),
    ("ملاحظات", 15),
    ("Age", 5),
    ("المستشفى", 20),
    ("Payment", 20),
    ("diagnosis", 25),
    ("Expected Payment", 15),
    ("Sticker image", 43),
    ("File name", 10)
  ]

  # Columns' name based on the excel_structure
  display_cols = [col[0] for col in excel_structure]

  # Filtered df to match these columns
  df_export = df[ [c for c in display_cols if c in df.columns] ]

  # 3- write patient_data into the excel sheet
  # in memory buffer
  output = BytesIO()

  with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df_export.to_excel(writer, index=False, sheet_name="Sheet1")

    # 4- insert images into the excel sheet "Sheet1"

    # worksheet configurations
    # Get the xlsxwriter objects that pandas is using under the hood
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    worksheet.right_to_left()

    # EXTRA, this is just to have all the columns' width fitted nicely
    for i, (col_name, width) in enumerate(excel_structure):
      worksheet.set_column(i, i, width)


    img_col_index = display_cols.index("Sticker image")
    # IN the original df to get image_data
    for i, row_data in df.iterrows():
      image_bytes = row_data.get('image_data')

      if image_bytes:

        # calculate excel row
        excel_row = i + 1 # note: row 0 is header

        worksheet.set_row(excel_row, 100) # current row height = 100

        # insert the image
        image_stream = BytesIO(image_bytes)

        worksheet.embed_image(
          excel_row,
          img_col_index, # Sticker image column
          "sticker.png", # Dummy file name
          {
            'image_data': image_stream,
            'x_scale': 0.5,
            'y_scale': 0.5,
            'object_position': 1
          }
        )

  output.seek(0)

  filename_str = datetime.datetime.now().strftime("Report_%Y-%m-%d_%H-%M.xlsx")
  return StreamingResponse(
    output,
    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    headers={"Content-Disposition": f"attachment; filename={filename_str}"}
  )
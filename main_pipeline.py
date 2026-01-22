import os
import cv2
import pandas as pd
import easyocr
from ultralytics import YOLO

# Modules
from OCR import clean_text, clean_age, get_best_ocr

""" CONFIG """
HUNTER_MODEL_PATH = 'models/detect/train1/weights/best.pt'
SURGEON_MODEL_PATH = 'models/surgeon/train_v1/weights/best.pt'
# test path to scan sheets (TO DO: take folder path from user via frontend)
INPUT_FOLDER = r"datasets/scan_sheets_test"
OUTPUT_EXCEL = "Final_Medical_Report.xlsx"
OCR_CONFIDENCE_THRESHOLD = 0.4

""" Model loading and OCR """
# 1- Load models
print("Loading models...")
hunter_model = YOLO(HUNTER_MODEL_PATH)
surgeon_model = YOLO(SURGEON_MODEL_PATH)
# 2- Load ocr
reader = easyocr.Reader(['en', 'ar'], gpu=True)

""" MAIN PROCESS """
final_data = []

# 1- Loop through every image in the folder
image_files = [file for file in os.listdir(INPUT_FOLDER) if file.lower().endswith(('.jpg', '.jpeg', '.png'))]

for filename in image_files:
    image_path = os.path.join(INPUT_FOLDER, filename)
    # 2- process each image
    print(f"Processing {filename}...")
    original_image = cv2.imread(image_path)
    if original_image is None:
        print(f"Couldn't read: {filename}")
        continue

    # 2- Find all stickers in the sheet (hunter model)
    hunter_results = hunter_model(original_image, verbose=False)
    if len(hunter_results[0].boxes) == 0:
        print(f"Couldn't detect any stickers in {filename}")
        continue

    # 2.5 LOOP through every sticker found
    for i, sticker_box in enumerate(hunter_results[0].boxes):
        # 2.5.1- Identify the Hospital
        hospital_id = int(sticker_box.cls[0])
        hospital_name = hunter_model.names[hospital_id]

        # 2.5.2- Crop the sticker in the sheet
        x1, y1, x2, y2 = map(int, sticker_box.xyxy[0])
        sticker_crop = original_image[y1:y2, x1:x2]

        # Safety Check: Skip if crop is tiny
        if sticker_crop.size == 0:
            continue

        # 3- Find fields inside the current sticker (surgeon model)
        surgeon_results = surgeon_model(sticker_crop, verbose=False)

        patient_info = {
            "File Name": filename,
            "Sticker image": f'=HYPERLINK("{os.path.abspath(image_path)}", "View Sheet")',
            "Hospital Name": hospital_name,
            "Name": "-",
            "Date": "-",
            "Age": "-",
            "Payment": "-"
        }

        # 3.5- process each field in the sticker
        names_map = surgeon_model.names
        for box in surgeon_results[0].boxes:
            cls_id = int(box.cls[0])
            class_name = names_map[cls_id]

            # crop the field
            bx1, by1, bx2, by2 = map(int, box.xyxy[0])
            field_cropped = sticker_crop[by1:by2, bx1:bx2]

            # OCR + safety logic
            text, confidence = get_best_ocr(reader, field_cropped)
            if confidence < OCR_CONFIDENCE_THRESHOLD:
                final_value = "-"
            else:
                final_value = clean_text(text)

            if class_name == "field_name":
                patient_info["Name"] = final_value
            elif class_name == "field_date":
                patient_info["Date"] = final_value
            elif class_name == "field_age":
                patient_info["Age"] = clean_age(final_value)
            elif class_name == "field_payment":
                patient_info["Payment"] = final_value

        final_data.append(patient_info)

""" SAVING DATA """
print("\nSaving Final Report...")
if final_data:
    df = pd.DataFrame(final_data)
    # Reorder columns
    cols = ["File Name", "Sticker image", "Hospital Name", "Name", "Date", "Age", "Payment"]
    # Only keep columns that actually exist in the dataframe to prevent errors
    cols = [c for c in cols if c in df.columns]
    df = df[cols]
    df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"Saved to: {OUTPUT_EXCEL}")
    print(f"Total Patients Found: {len(df)}")
else:
    print("No data extracted. Check your images.")
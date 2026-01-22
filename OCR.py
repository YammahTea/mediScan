import easyocr
import cv2
import re
import numpy as np

# helper functions
def preprocess_image(img):
    """
    Magic Filter: Makes text pop out for better OCR.
    1- Grayscale
    2- Upscale (2x)
    3= Threshold (Black text on White bg)
    """
    # Convert to gray
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Upscale (Zoom in) - makes small text readable
    scaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # Threshold (Binarization) - strict black and white
    _, thresh = cv2.threshold(scaled, 120, 255, cv2.THRESH_BINARY)

    return thresh

def clean_text(text):
    """
    Cleans up OCR mess
    Example: "Name: Mike" -> "Mike"
    """
    if not text:
        return "-"

    text = text.strip()

    # just to fix common OCR typos in dates (e.g., "202{" -> "2025")
    text = text.replace("{", "5").replace('}', '5').replace('[', '5')

    return text


def clean_age(text):
  """
  Cleans the age field in the sticker to a standard format
  """
  if not text: return "-"

  # If it sees "Years", "Months", just keep the first number
  # Example: "93 Years 8 Months" -> "93"
  match = re.search(r'\d+', text)
  if match:
    return match.group(0)
  return "-"

def get_best_ocr(reader, crop_img):
    """
    Read text from the cropped image
    :return: (text, confidence)
    """
    # 1- process the image
    processed_img = preprocess_image(crop_img)

    # 2- read text
    # detail=1 gives boxes+text+conf
    results = reader.readtext(processed_img, detail=1)

    if not results:
        return "-", 0.0

    # 3- detect language and sort
    # note: easyocr usually scans Top->Bottom, Left->Right

    # 3.1- check if the scanned text is arabic to make it read Right->Left
    is_arabic = False
    for (_, text, _) in results:
        if any('\u0600' <= char <= '\u06FF' for char in text):
            is_arabic = True
            break

    if is_arabic:
        results.sort(key=lambda x: x[0][0][0], reverse=True)
    else: # english
        results.sort(key=lambda x: x[0][0][0], reverse=False)

    full_text = []
    total_confidence = 0

    for (_, text, confidence) in results:
        full_text.append(text)
        total_confidence += confidence

    avg_confidence = total_confidence / len(results)

    return " ".join(full_text), avg_confidence
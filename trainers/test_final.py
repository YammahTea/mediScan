from ultralytics import YOLO
import os

# 1- Load the model from train4 (my best model so far)
model_path = '../models/detect/train4/weights/best.pt'

if not os.path.exists(model_path):
    print("Didn't find the model file")
    exit()

print(f"Loading the model: {model_path}")
model = YOLO(model_path)

# 2- Path to the images to test
test_image_path = r"E:\PycharmProjects\mediScan\datasets\scan_sheets_test"

# 3- Show and Save the result to a SINGLE folder
for filename in os.listdir(test_image_path):
  test_image = os.path.join(test_image_path, filename)
  results = model.predict(
    test_image,
    save=True,
    show=False,
    project='./models/detect',  # Base directory
    name='predictions',  # Folder name
    exist_ok=True  # reuse the same folder
  )
print("Success! Check 'models/detect/predictions' folder.")
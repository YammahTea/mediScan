from ultralytics import YOLO

def main():
  # Load model
  # model = YOLO('yolov8s.pt')

  # # epochs=80 (sessions) || imgsz=960 (resolution 960x960)
  # print("Starting training...")
  # results = model.train(data='../data.yaml',
  #                       epochs=80,
  #                       imgsz=960,
  #                       batch=8,
  #                       device=0, # Gpu
  #                       workers=0
  #                       project = '../models/detect_sheet',
  #                       name = 'train_v2'
  #                       )
  pass

if __name__ == '__main__':
  main()

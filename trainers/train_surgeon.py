from ultralytics import YOLO
import torch
import gc

def on_train_epoch_end(trainer):
  """
  Cleans up the RAM after each epoch to prevent crashes
  """
  torch.cuda.empty_cache()
  gc.collect()

def main():

  # 1- load model
  model = YOLO('../yolov8n.pt')

  # 2- clean up
  model.add_callback("on_train_epoch_end", on_train_epoch_end)

  # 3- train the model
  print("Starting training...")
  results = model.train(
    data='../data_surgeon.yaml',
    epochs=100,
    imgsz=640,
    batch=4,
    device=0,
    workers=0, # requirement for windows
    degrees=10.0, # to handle tilted stickers
    scale=0.5, # handle size difference
    patience=20, # Stop early if it stops learning
    project='../models/surgeon',
    name='train_v1'
  )

if __name__ == '__main__':
  main()
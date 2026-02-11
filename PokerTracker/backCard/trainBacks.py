from ultralytics import YOLO
import torch

device = 0 if torch.cuda.is_available() else 'cpu'
print(f"Using device: {device}")

model = YOLO('yolov8n.pt')

model.train(
    data='/home/evan/hoyleed-senior-design/backCard/cards.yaml', 
    epochs=500, 
    imgsz=640, 
    device=device,
    batch=32  
)
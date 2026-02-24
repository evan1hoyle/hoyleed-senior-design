import cv2
from ultralytics import YOLO

model = YOLO('runs/detect/train6/weights/best.pt')



# 2. Open the camera
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 3. Run inference
    # stream=True is more memory efficient for video
    # conf=0.5 ignores weak detections (adjust as needed)
    results = model(frame, stream=True, conf=0.3)

    for r in results:
        boxes = r.boxes
        for box in boxes:
            # Get coordinates for the bounding box
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            # Get confidence and class name
            conf = box.conf[0]
            cls = int(box.cls[0])
            label = model.names[cls]

            # 4. Draw on the frame
            # Green box for detected card back
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f'{label} {conf:.2f}', (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Display the result
    cv2.imshow("YOLOv8 Card Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
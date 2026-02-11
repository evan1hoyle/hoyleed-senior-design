import cv2
import json
import time
import os
import numpy as np
import select_zones
import argparse
from sahi import AutoDetectionModel
from sahi.predict import get_prediction


parser = argparse.ArgumentParser()
parser.add_argument('-z', '--setzones', action='store_true', help='Sets zones manually')
args = parser.parse_args()

X, Y = 1920, 1080
FLOP_HAND_SIZE = 5 

detection_model = AutoDetectionModel.from_pretrained(
    model_type="ultralytics",
    model_path="/home/evan/projects/hoyleed-senior-design/PokerTracker/chips/best5.pt",
    confidence_threshold=0.5,
    device="cuda" 
)

cap = cv2.VideoCapture(0)
cap.set(3, X)
cap.set(4, Y)

if args.setzones:
    players, _ = select_zones.set_zones(cap, cv2, FLOP_HAND_SIZE)
else:
    players, _ = select_zones.fetch_zones()

print("Starting Zone-based Chip Detection. Press 'q' to quit.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    all_detections = []
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")

    for p_idx, hand_zones in enumerate(players):
        for z_idx, (zx, zy, zw, zh) in enumerate(hand_zones):
            roi = frame[int(zy):int(zy+zh), int(zx):int(zx+zw)]
            
            if roi.size == 0:
                continue


            result = get_prediction(roi, detection_model)

            for prediction in result.object_prediction_list:
                bbox = prediction.bbox.to_xyxy() # [lx1, ly1, lx2, ly2] (local to crop)
                label = prediction.category.name
                score = prediction.score.value

                gx1, gy1 = int(bbox[0] + zx), int(bbox[1] + zy)
                gx2, gy2 = int(bbox[2] + zx), int(bbox[3] + zy)

                chip_data = {
                    "player_index": p_idx,
                    "zone_index": z_idx,
                    "label": label,
                    "confidence": round(float(score), 3),
                    "bbox": [gx1, gy1, gx2, gy2]
                }
                all_detections.append(chip_data)
                

                cv2.rectangle(frame, (gx1, gy1), (gx2, gy2), (0, 255, 0), 2)
                cv2.putText(frame, f"P{p_idx+1}: {label}", (gx1, gy1-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        for (zx, zy, zw, zh) in hand_zones:
            cv2.rectangle(frame, (int(zx), int(zy)), (int(zx+zw), int(zy+zh)), (0, 0, 255), 1)

    cv2.imshow("Zone Chip Detection", frame)

    output_file = "data/detected_chips.json"
    with open(output_file, "w") as f:
        json.dump({"timestamp": current_time, "detections": all_detections}, f, indent=4)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
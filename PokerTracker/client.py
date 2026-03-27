import cv2
import numpy as np
import time
import requests
import base64
import argparse
import select_zones
import uuid

SERVER_URL = "http://127.0.0.1:5000/process_frame" 
X, Y = 1920, 1080
FLOP_HAND_SIZE = 5
CLIENT_ID = str(uuid.uuid4())[:8]

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', action='store_true')
parser.add_argument('-z', '--setzones', action='store_true')
parser.add_argument('-pz','--playerzone', type=str, help='name of custom player zone file')
parser.add_argument('--video', type=str, help='Path to test video file')
parser.add_argument('--loop', action='store_true', help='Loop the video')
args = parser.parse_args()

def apply_clahe(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    return cv2.cvtColor(cv2.merge((cl,a,b)), cv2.COLOR_LAB2BGR)

def open_first_available_camera():
    for index in range(10):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                if args.verbose:
                    print(f"Successfully opened camera with index {index}")
                return cap
            else:
                cap.release()
        else:
            cap.release() 
    raise RuntimeError("Error: Could not find an available camera.")
    return None

def get_video_source():
    if args.video:
        if args.verbose:
            print(f"Opening video file: {args.video}")
        cap = cv2.VideoCapture(args.video)
        if not cap.isOpened():
            raise FileNotFoundError(f"Could not open video file: {args.video}")
        return cap
    else:
        return open_first_available_camera()

cap = get_video_source()
cap.set(3, X)
cap.set(4, Y)

if args.setzones:
    players, flop_slots = select_zones.set_zones(cap, cv2, FLOP_HAND_SIZE)
else:
    if(args.playerzone):
        players, flop_slots = select_zones.fetch_zones(P_PATH=args.playerzone)
    else:
         players, flop_slots = select_zones.fetch_zones()

while True:
    success, img = cap.read()
    if not success:
            if args.video and args.loop:
                if args.verbose:
                    print("Looping video...")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, img = cap.read()
            else:
                break 
    curr_t = time.time()
    img = cv2.flip(img,-1)

    p_slots = [(card, 'player', p_idx, c_idx) for p_idx, hand in enumerate(players) for c_idx, card in enumerate(hand)]
    f_slots = [(card, 'flop', 0, f_idx) for f_idx, card in enumerate(flop_slots)]
    all_slots = p_slots + f_slots

    encoded_crops = []
    sanitized_slots = []

    for (rect, label, p_idx, c_idx) in all_slots:
        x, y, w, h = [int(v) for v in rect]
        
        crop = img[y:y+h, x:x+w]
        if crop.size > 0:
            crop = apply_clahe(crop)
            _, buffer = cv2.imencode('.jpg', crop)
            encoded_crops.append(base64.b64encode(buffer).decode('utf-8'))
            
            sanitized_slots.append({
                "rect": [int(x), int(y), int(w), int(h)],
                "label": str(label),
                "p_idx": int(p_idx),
                "c_idx": int(c_idx)
            })

    payload = {
            "client_id": CLIENT_ID, 
            "crops": encoded_crops,
            "slots": sanitized_slots  
        }

    for p_idx, hand in enumerate(players):
        for c_idx, rect in enumerate(hand):
            x, y, w, h = [int(v) for v in rect]
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(img, f"P{p_idx} C{c_idx}", (x, y - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

    for f_idx, rect in enumerate(flop_slots):
        x, y, w, h = [int(v) for v in rect]
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(img, f"Flop {f_idx}", (x, y - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)


    try:
        response = requests.post(SERVER_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            detections = data.get('detections', [])

            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                label = det['label']
                color = det['color'] 

                cv2.rectangle(img, (x1, y1), (x2, y2), tuple(color), 2)
                cv2.putText(img, label, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, tuple(color), 2)

    except Exception as e:
        print(f"Connection Error: {e}")

    cv2.imshow('{feed} Feed'.format(feed=CLIENT_ID), img)
    if cv2.waitKey(1) == ord('q'): break

cap.release()
cv2.destroyAllWindows()
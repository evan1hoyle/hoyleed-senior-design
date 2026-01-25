import cv2
import numpy as np
from ultralytics import YOLO
import time
import os
import json
import calcWinner

X, Y = 1920, 1080
CARD_TIMEOUT_SECONDS = 1.0 
CARD_IMAGES_DIR = "card_images"
CARD_IMAGE_WIDTH, CARD_IMAGE_HEIGHT = 100, 140 
PLAYER_HAND_SIZE, FLOP_HAND_SIZE = 2, 5
COLOR_DIFF_THRESHOLD = 30 
TABLE_FELT_BGR = [0, 0, 0]

def open_first_available_camera():
    for index in range(10):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"Successfully opened camera with index {index}")
                return cap
            else:
                cap.release()
        else:
            cap.release() 
    print("Error: Could not find an available camera.")
    return None


cap = open_first_available_camera()
cap.set(3, X)
cap.set(4, Y)

model = YOLO("yolov8s_playing_cards.pt")

classNames = [
    '10C', '10D', '10H', '10S', '2C', '2D', '2H', '2S', '3C', '3D', 
    '3H', '3S', '4C', '4D', '4H', '4S', '5C', '5D', '5H', '5S', 
    '6C', '6D', '6H', '6S', '7C', '7D', '7H', '7S', '8C', '8D', 
    '8H', '8S', '9C', '9D', '9H', '9S', 'AC', 'AD', 'AH', 'AS', 
    'JC', 'JD', 'JH', 'JS', 'KC', 'KD', 'KH', 'KS', 'QC', 'QD', 
    'QH', 'QS'
]

def get_card_file_name(card_name):
    rank, suit = card_name[:-1], card_name[-1]
    rank_map = {'A': 'ace', 'K': 'king', 'Q': 'queen', 'J': 'jack', '10': '10'}
    suit_map = {'C': 'clubs', 'D': 'diamonds', 'H': 'hearts', 'S': 'spades'}
    rank_full = rank_map.get(rank, rank)
    suit_full = suit_map.get(suit)
    return f"{rank_full}_of_{suit_full}.png" if suit_full else None

CARD_IMAGE_CACHE = {}
def load_card_image(card_name):
    if card_name in CARD_IMAGE_CACHE: return CARD_IMAGE_CACHE[card_name]
    file_name = get_card_file_name(card_name)
    if not file_name: return None
    file_path = os.path.join(CARD_IMAGES_DIR, file_name)
    if not os.path.exists(file_path): return None
    img = cv2.imread(file_path)
    if img is None: return None
    resized_img = cv2.resize(img, (CARD_IMAGE_WIDTH, CARD_IMAGE_HEIGHT))
    CARD_IMAGE_CACHE[card_name] = resized_img
    return resized_img

def select_zones(cap):
    answer = input("Do you want to draw boxs? (yes/no): ").lower()
    if answer == "yes" or answer == "y":
        f_slots = []
        players = []
        success, frame = cap.read()
        if not success: return [], []
        
        cv2.namedWindow("Setup", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Setup", 1280, 720)
        
        # Select Player Slots
        while True:
            key = cv2.waitKey(0) & 0xFF

            if key == 32:  # Space bar
                p_slots = []
                # selectROI naturally waits for you to finish the selection
                roi = cv2.selectROI("Setup", frame, False)
                
                # Only add if the ROI has a width/height (prevents empty clicks)
                if roi[2] > 0 and roi[3] > 0:
                    p_slots.append(roi)
                    players.append(p_slots)
                    print(f"Added player at {roi}. Press Space for more or Enter to finish.")
                else:
                    print("Selection cancelled.")

            elif key in [13, 10]:  # Enter key
                print("Selection complete.")
                break
                
        # Select Flop Slots
        for i in range(FLOP_HAND_SIZE):
            print(f"Draw Flop Slot {i+1} and press ENTER")
            roi = cv2.selectROI("Setup", frame, False)
            f_slots.append(roi)
            
        cv2.destroyWindow("Setup")

        with open("data/p_slots.json", "w") as file:
            json.dump(players, file, indent=4) 
        with open("data/f_slots.json", "w") as file:
            json.dump(f_slots, file, indent=4) 

    elif answer == "no" or answer == "n":
        with open("data/p_slots.json", "r") as file:
            players = json.load(file)
        with open("data/f_slots.json", "r") as file:
            f_slots = json.load(file)


    else:
        print("Invalid input. Please enter 'yes' or 'no'.")

    print(players)
    print(f_slots)
    return players, f_slots


players, flop_slots = select_zones(cap)
player_cards = {} 
flop_cards = {}

while True:
    success, img = cap.read()
    if not success: break
    curr_t = time.time()

    p_slots = []
    for p_idx, hand in enumerate(players, start=0):
        for c_idx, card in enumerate(hand, start=0):
            p_slots.append((card, 'player', p_idx, c_idx))

    flop_labeled = []
    for f_idx, card in enumerate(flop_slots, start=0):
        flop_labeled.append((card, 'flop', 0,f_idx))

    all_slots = p_slots + flop_labeled
    crops = []
    for (x, y, w, h), label, p_idx,c_idx in all_slots:
        crop = img[int(y):int(y+h), int(x):int(x+w)]
        if crop.size > 0:
            crops.append(crop)
        else:
            crops.append(np.zeros((100, 100, 3), dtype=np.uint8))

    results = model(crops, conf=0.4, verbose=False)

    # 3. Update detected cards
    for i, r in enumerate(results):
        best_box = None
        max_conf = 0

        (roi_x, roi_y, roi_w, roi_h), label, p_idx,c_idx = all_slots[i]
    
        for box in r.boxes:
            # 1. Get local coordinates (relative to the small crop)
            lx1, ly1, lx2, ly2 = [int(val) for val in box.xyxy[0]]
            
            # 2. Translate to global coordinates (relative to the 1080p frame)
            gx1, gy1 = roi_x + lx1, roi_y + ly1
            gx2, gy2 = roi_x + lx2, roi_y + ly2

            # 3. Draw detection directly onto the original high-res image
            cv2.rectangle(img, (gx1, gy1), (gx2, gy2), (0, 255, 0), 2)
            
            card_name = classNames[int(box.cls[0])]
            conf = box.conf[0].item()
            cv2.putText(img, f"{card_name} {conf:.2f}", (gx1, gy1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        unique_detections = {}
        for box in r.boxes:
            conf = box.conf[0].item()
            card_name = classNames[int(box.cls[0])]
            
            if card_name not in unique_detections or conf > unique_detections[card_name]['conf']:
                unique_detections[card_name] = {'name': card_name, 'conf': conf}

        sorted_cards = sorted(unique_detections.values(), key=lambda x: x['conf'], reverse=True)

        if label == "player":
            if sorted_cards:
                if p_idx not in player_cards:
                    player_cards[p_idx] = {}

                for i, card in enumerate(sorted_cards[:2]):
                    player_cards[p_idx][i] = {'name': card['name'], 'conf': card['conf'], 'ts': curr_t}
            else:
                roi_img = img[roi_y : roi_y + roi_h, roi_x : roi_x + roi_w]
                
                if roi_img.size > 0:
                    # Calculate the average color of the slot
                    avg_bgr = cv2.mean(roi_img)[:3]
                    
                    # Calculate Euclidean distance between average color and table felt
                    dist = np.linalg.norm(np.array(avg_bgr) - np.array(TABLE_FELT_BGR))
                    
                    if dist > COLOR_DIFF_THRESHOLD:
                        # We found something that isn't the table, but isn't a face-up card
                        card_name = "DN"
                        
                        # Draw the "DN" label on the frame
                        cv2.rectangle(img, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (255, 255, 0), 2)
                        cv2.putText(img, "DN", (roi_x, roi_y - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

                        # Store in your data structures
                        if label == "player":
                            if p_idx not in player_cards: player_cards[p_idx] = {}
                            player_cards[p_idx][0] = {'name': 'DN', 'conf': 1.0, 'ts': curr_t}
                        elif label == "flop":
                            flop_cards[c_idx] = {'name': 'DN', 'conf': 1.0, 'ts': curr_t}

        elif label == "flop":
            max_conf = 0
            best_box = None
            for box in r.boxes:
                if box.conf[0] > max_conf:
                    max_conf = box.conf[0].item()
                    best_box = box
                    
            if best_box:
                card_name = classNames[int(best_box.cls[0])]
                flop_cards[c_idx] = {'name': card_name, 'conf': max_conf, 'ts': curr_t}


    # 4. Clear expired cards (Timeout)
    player_cards = {
        p_id: {
            c_idx: data for c_idx, data in cards.items() 
            if curr_t - data['ts'] < CARD_TIMEOUT_SECONDS
        }
        for p_id, cards in player_cards.items()
    }
    flop_cards = {
        c_idx: data for c_idx, data in flop_cards.items() 
        if curr_t - data['ts'] < CARD_TIMEOUT_SECONDS
    }

    # 5. Drawing Zones on Main Feed
    for player_num,player in enumerate(players):
        for box_num, (x, y, w, h) in enumerate(player):
            color = (0, 255, 0) if box_num in player_cards else (0, 0, 255)
            cv2.rectangle(img, (int(x), int(y)), (int(x+w), int(y+h)), color, 2)
            cv2.putText(img, f"Player {player_num+1} Card {box_num+1}",(int(x), int(y-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    for i, (x, y, w, h) in enumerate(flop_slots):
        color = (0, 255, 0) if i in flop_cards else (255, 0, 0)
        cv2.rectangle(img, (int(x), int(y)), (int(x+w), int(y+h)), color, 2)
        cv2.putText(img, f"Flop {i+1}", (int(x), int(y-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # 6. Build Graphical UI Window
    ui_w = (5 * (CARD_IMAGE_WIDTH + 20)) + 40
    ui_h = 450
    ui_img = np.zeros((ui_h, ui_w, 3), dtype=np.uint8)
    
    with open("data/flop_cards.json", "w") as file:
        json.dump(flop_cards, file, indent=4) 
    with open("data/player_cards.json", "w") as file:
        json.dump(player_cards, file, indent=4) 

    # 7. Show Windows
    cv2.imshow('Main Camera Feed (R to Reset Zones, Q to Quit)', img)

    key = cv2.waitKey(1)
    if key == ord('q'):
        break
    elif key == ord('r'):
        player_slots, flop_slots = select_zones(cap)
        player_cards.clear()
        flop_cards.clear()

    calcWinner.evaluate_winner()


cap.release()
cv2.destroyAllWindows()
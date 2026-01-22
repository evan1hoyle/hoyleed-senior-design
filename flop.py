import cv2
import numpy as np
from ultralytics import YOLO
import time
import os
import json


# --- Configuration ---
X, Y = 1920, 1080
CARD_TIMEOUT_SECONDS = 4.0 
CARD_IMAGES_DIR = "card_images"
CARD_IMAGE_WIDTH, CARD_IMAGE_HEIGHT = 100, 140 
PLAYER_HAND_SIZE, FLOP_HAND_SIZE = 2, 5

# --- Initialize YOLO ---
# Note: Ensure this file is in your script directory
model = YOLO("yolov8s_playing_cards.pt")

classNames = [
    '10C', '10D', '10H', '10S', '2C', '2D', '2H', '2S', '3C', '3D', 
    '3H', '3S', '4C', '4D', '4H', '4S', '5C', '5D', '5H', '5S', 
    '6C', '6D', '6H', '6S', '7C', '7D', '7H', '7S', '8C', '8D', 
    '8H', '8S', '9C', '9D', '9H', '9S', 'AC', 'AD', 'AH', 'AS', 
    'JC', 'JD', 'JH', 'JS', 'KC', 'KD', 'KH', 'KS', 'QC', 'QD', 
    'QH', 'QS'
]

# --- Helper functions ---

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
        print("Continuing...")
        
        f_slots = []
        players = []
        success, frame = cap.read()
        if not success: return [], []
        
        cv2.namedWindow("Setup - Draw 5 Boxes", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Setup - Draw 5 Boxes", 1280, 720)
        
        # Select Player Slots
        while True:
            answer = input("Do you want add another player? (yes/no): ").lower()
            if answer == "yes" or answer == "y":
                p_slots = []
                for i in range(PLAYER_HAND_SIZE):
                    print(f"Draw Player Slot {i+1} and press ENTER")
                    roi = cv2.selectROI("Setup - Draw 5 Boxes", frame, False)
                    p_slots.append(roi)
                players.append(p_slots)

            elif answer == "no" or answer == "n":
                break
                
        # Select Flop Slots
        for i in range(FLOP_HAND_SIZE):
            print(f"Draw Flop Slot {i+1} and press ENTER")
            roi = cv2.selectROI("Setup - Draw 5 Boxes", frame, False)
            f_slots.append(roi)
            
        cv2.destroyWindow("Setup - Draw 5 Boxes")

        with open("p_slots.json", "w") as file:
            json.dump(players, file, indent=4) 
        with open("f_slots.json", "w") as file:
            json.dump(f_slots, file, indent=4) 

    elif answer == "no" or answer == "n":
        with open("p_slots.json", "r") as file:
            players = json.load(file)
        with open("f_slots.json", "r") as file:
            f_slots = json.load(file)


    else:
        print("Invalid input. Please enter 'yes' or 'no'.")

    print(players)
    print(f_slots)
    return players, f_slots

# --- Main Logic ---
cap = cv2.VideoCapture(1)
cap.set(3, X)
cap.set(4, Y)

# Initial Setup
players, flop_slots = select_zones(cap)
# Data structure: {slot_index: {'name': str, 'conf': float, 'ts': float}}
player_data = {} 
flop_data = {}

while True:
    success, img = cap.read()
    if not success: break
    curr_t = time.time()


    p_slots = [(x, 'player') for sublist in players for x in sublist]
    flop_labeled = [(x, 'flop') for x in flop_slots]
    all_slots = p_slots + flop_labeled
    crops = []
    for (x, y, w, h), label in all_slots:
        crop = img[int(y):int(y+h), int(x):int(x+w)]
        if crop.size > 0:
            crops.append(crop)
        else:
            crops.append(np.zeros((100, 100, 3), dtype=np.uint8))

    # 2. Batch Inference
    # Processing all 5 zones in one go is very efficient
    results = model(crops, conf=0.4, verbose=False)

    # 3. Update detected cards
    for i, r in enumerate(results):
        best_box = None
        max_conf = 0

        (roi_x, roi_y, roi_w, roi_h), label = all_slots[i]
    
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
        
        for box in r.boxes:
            if box.conf[0] > max_conf:
                max_conf = box.conf[0].item()
                best_box = box
        
        if best_box:
            card_name = classNames[int(best_box.cls[0])]
            if label == "player":
                player_data[i] = {'name': card_name, 'conf': max_conf, 'ts': curr_t}
            elif label =="flop":
                flop_data[i - PLAYER_HAND_SIZE] = {'name': card_name, 'conf': max_conf, 'ts': curr_t}

    # 4. Clear expired cards (Timeout)
    player_data = {k: v for k, v in player_data.items() if curr_t - v['ts'] < CARD_TIMEOUT_SECONDS}
    flop_data = {k: v for k, v in flop_data.items() if curr_t - v['ts'] < CARD_TIMEOUT_SECONDS}

    # 5. Drawing Zones on Main Feed
    for player_num,player in enumerate(players):
        for box_num, (x, y, w, h) in enumerate(player):
            color = (0, 255, 0) if box_num in player_data else (0, 0, 255)
            cv2.rectangle(img, (int(x), int(y)), (int(x+w), int(y+h)), color, 2)
            cv2.putText(img, f"Player {player_num+1} Card {box_num+1}",(int(x), int(y-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    for i, (x, y, w, h) in enumerate(flop_slots):
        color = (0, 255, 0) if i in flop_data else (255, 0, 0)
        cv2.rectangle(img, (int(x), int(y)), (int(x+w), int(y+h)), color, 2)
        cv2.putText(img, f"Flop {i+1}", (int(x), int(y-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # 6. Build Graphical UI Window
    ui_w = (5 * (CARD_IMAGE_WIDTH + 20)) + 40
    ui_h = 450
    ui_img = np.zeros((ui_h, ui_w, 3), dtype=np.uint8)

    # Render Player UI
    cv2.putText(ui_img, "PLAYER HAND", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    for i in player_data:
        x_off = 20 + (i * (CARD_IMAGE_WIDTH + 20))
        cv2.rectangle(ui_img, (x_off, 60), (x_off+CARD_IMAGE_WIDTH, 60+CARD_IMAGE_HEIGHT), (50, 50, 50), 1)
        if i in player_data:
            c_img = load_card_image(player_data[i]['name'])
            if c_img is not None:
                ui_img[60:60+CARD_IMAGE_HEIGHT, x_off:x_off+CARD_IMAGE_WIDTH] = c_img
                cv2.putText(ui_img, f"{player_data[i]['conf']:.2f}", (x_off, 220), 1, 1, (255,255,255), 1)

    # Render Flop UI
    cv2.putText(ui_img, "FLOP", (20, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
    for idx, (key, data) in enumerate(flop_data.items()):
        x_off = 20 + (idx * (CARD_IMAGE_WIDTH + 20))
        
        # Safety check: Ensure the slice doesn't exceed image boundaries
        if x_off + CARD_IMAGE_WIDTH <= ui_img.shape[1]:
            c_img = load_card_image(data['name'])
            if c_img is not None:
                # Check if c_img needs resizing to match CARD_IMAGE constants
                if c_img.shape[0] != CARD_IMAGE_HEIGHT or c_img.shape[1] != CARD_IMAGE_WIDTH:
                    c_img = cv2.resize(c_img, (CARD_IMAGE_WIDTH, CARD_IMAGE_HEIGHT))
                    
                ui_img[280:280+CARD_IMAGE_HEIGHT, x_off:x_off+CARD_IMAGE_WIDTH] = c_img
                cv2.putText(ui_img, f"{data['conf']:.2f}", (x_off, 440), 1, 1, (255,255,255), 1)

    # 7. Show Windows
    cv2.imshow('Main Camera Feed (R to Reset Zones, Q to Quit)', img)
    cv2.imshow('Detected Cards UI', ui_img)

    key = cv2.waitKey(1)
    if key == ord('q'):
        break
    elif key == ord('r'):
        player_slots, flop_slots = select_zones(cap)
        player_data.clear()
        flop_data.clear()


cap.release()
cv2.destroyAllWindows()
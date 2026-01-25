import cv2
import numpy as np
from ultralytics import YOLO
import time
import os
import json
import calcWinner
import select_zones
import argparse

X, Y = 1920, 1080
CARD_TIMEOUT_SECONDS = 0.5
CARD_IMAGES_DIR = "card_images"
CARD_IMAGE_WIDTH, CARD_IMAGE_HEIGHT = 100, 140 
PLAYER_HAND_SIZE, FLOP_HAND_SIZE = 2, 5
DN_CONF_MIN = 0.8


parser = argparse.ArgumentParser(description='A sample program with a flag.')
parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
parser.add_argument('-z', '--setzones', action='store_true', help='Sets zones')
args = parser.parse_args()


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


cap = open_first_available_camera()
cap.set(3, X)
cap.set(4, Y)

model = YOLO("yolov8s_playing_cards.pt")
model.to('cuda')


modelBack = YOLO('runs/detect/train6/weights/best.pt')
modelBack.to('cuda')


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

if args.setzones:
    players, flop_slots = select_zones.set_zones(cap,cv2,FLOP_HAND_SIZE)
else:
    players, flop_slots = select_zones.fetch_zones()


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
    resultsBack = modelBack(crops, conf=DN_CONF_MIN, verbose=False)

    for i, r in enumerate(results):
            (roi_x, roi_y, roi_w, roi_h), label, p_idx, c_idx = all_slots[i]
            r_back = resultsBack[i]
            
            if len(r.boxes) > 0:
                for box in r.boxes:
                    lx1, ly1, lx2, ly2 = [int(val) for val in box.xyxy[0]]
                    gx1, gy1, gx2, gy2 = roi_x + lx1, roi_y + ly1, roi_x + lx2, roi_y + ly2

                    cv2.rectangle(img, (gx1, gy1), (gx2, gy2), (0, 255, 0), 2)
                    card_name = classNames[int(box.cls[0])]
                    conf = box.conf[0].item()
                    cv2.putText(img, f"{card_name} {conf:.2f}", (gx1, gy1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                unique_detections = {}
                for box in r.boxes:
                    conf = box.conf[0].item()
                    name = classNames[int(box.cls[0])]
                    if args.verbose:
                        print(f"[VERBOSE] Detected {name} in {label} slot {i} (Conf: {conf:.2f})")
                    if name not in unique_detections or conf > unique_detections[name]['conf']:
                        unique_detections[name] = {'name': name, 'conf': conf}
                
                sorted_cards = sorted(unique_detections.values(), key=lambda x: x['conf'], reverse=True)
                if label == "player":
                    if p_idx not in player_cards: player_cards[p_idx] = {}
                    for idx, card in enumerate(sorted_cards[:2]):
                        player_cards[p_idx][idx] = {'name': card['name'], 'conf': card['conf'], 'ts': curr_t}
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

            elif len(r_back.boxes) > 0:
                for box_back in r_back.boxes:
                    blx1, bly1, blx2, bly2 = [int(val) for val in box_back.xyxy[0]]
                    bgx1, bgy1, bgx2, bgy2 = roi_x + blx1, roi_y + bly1, roi_x + blx2, roi_y + bly2
                    
                    conf = box_back.conf[0].item()

                    if args.verbose:
                        print(f"[VERBOSE] Detected DN in {label} slot {i} (Conf: {conf:.2f})")

                    if label == "player":
                        cv2.rectangle(img, (bgx1, bgy1), (bgx2, bgy2), (255, 255, 0), 2)
                        cv2.putText(img, f"DN {conf:.2f}", (bgx1, bgy1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)


                if label == "player":
                    if p_idx not in player_cards: player_cards[p_idx] = {}
                    for idx in range(min(len(r_back.boxes), 2)):
                        player_cards[p_idx][idx] = {'name': 'DN', 'conf': r_back.boxes[idx].conf[0].item(), 'ts': curr_t}



    if args.verbose:
        for p_id, cards in player_cards.items():
            for c_idx, data in cards.items():
                if curr_t - data['ts'] >= CARD_TIMEOUT_SECONDS:
                    print(f"[TIMEOUT] Player {p_id+1}, Card Slot {c_idx+1} ({data['name']}) removed after {CARD_TIMEOUT_SECONDS}s")
    if args.verbose:
        for c_idx, data in flop_cards.items():
            if curr_t - data['ts'] >= CARD_TIMEOUT_SECONDS:
                print(f"[TIMEOUT] Flop Slot {c_idx+1} ({data['name']}) removed after {CARD_TIMEOUT_SECONDS}s")

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


    for player_num,player in enumerate(players):
        for box_num, (x, y, w, h) in enumerate(player):
            color = (0, 255, 0) if box_num in player_cards else (0, 0, 255)
            cv2.rectangle(img, (int(x), int(y)), (int(x+w), int(y+h)), color, 2)
            cv2.putText(img, f"Player {player_num+1} Card {box_num+1}",(int(x), int(y-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    for i, (x, y, w, h) in enumerate(flop_slots):
        color = (0, 255, 0) if i in flop_cards else (255, 0, 0)
        cv2.rectangle(img, (int(x), int(y)), (int(x+w), int(y+h)), color, 2)
        cv2.putText(img, f"Flop {i+1}", (int(x), int(y-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    ui_w = (5 * (CARD_IMAGE_WIDTH + 20)) + 40
    ui_h = 450
    ui_img = np.zeros((ui_h, ui_w, 3), dtype=np.uint8)

    if args.verbose:
        active_players = [p for p, cards in player_cards.items() if len(cards) > 0]
        active_flop = len(flop_cards)
        print(f"--- Frame Summary ---")
        print(f"Active Players: {active_players} | Cards on Flop: {active_flop}")

        processing_time = (time.time() - curr_t) * 1000
        print(f"Frame Processing Time: {processing_time:.2f}ms")
        
    with open("data/flop_cards.json", "w") as file:
        json.dump(flop_cards, file, indent=4) 
    with open("data/player_cards.json", "w") as file:
        json.dump(player_cards, file, indent=4) 

    cv2.imshow('Main Camera Feed (R to Reset Zones, Q to Quit)', img)

    key = cv2.waitKey(1)
    if key == ord('q'):
        break
    elif key == ord('r'):
        player_slots, flop_slots = select_zones(cap)
        player_cards.clear()
        flop_cards.clear()
    
    try:
        calcWinner.evaluate_winner()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


cap.release()
cv2.destroyAllWindows()
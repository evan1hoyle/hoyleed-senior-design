import cv2
import numpy as np
from ultralytics import YOLO
import time
import os
import json
import calcWinner
import select_zones
import argparse
import base64
from flask import Flask, request, jsonify
from sahi import AutoDetectionModel
from sahi.predict import get_prediction



X, Y = 1920, 1080
CARD_TIMEOUT_SECONDS = 2
CARD_IMAGES_DIR = "PokerTracker/card_images"
CARD_IMAGE_WIDTH, CARD_IMAGE_HEIGHT = 100, 140 
PLAYER_HAND_SIZE, FLOP_HAND_SIZE = 2, 5
DN_CONF_MIN = 0.80


parser = argparse.ArgumentParser(description='A sample program with a flag.')
parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
args = parser.parse_args()



model = YOLO("PokerTracker/models/yolov8s_playing_cards.pt")
model.to('cuda')

modelBack = YOLO('PokerTracker/backCard/runs/detect/train6/weights/best.pt')
modelBack.to('cuda')

detection_model = AutoDetectionModel.from_pretrained(
    model_type="ultralytics",
    model_path="/home/evan/Documents/senior-design/hoyleed-senior-design/PokerTracker/chips/best5.pt",
    confidence_threshold=0.5,
    device="cuda" 
)

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


global player_cards 
player_cards  = {} 

global flop_cards 
flop_cards= {}

global players, flop_slots
players, flop_slots = select_zones.fetch_zones()

app = Flask(__name__)
@app.route('/process_frame', methods=['POST'])
def process_frame():
    global player_cards, flop_cards, players, flop_slots
    curr_t = time.time()

    data = request.json
    client_id = data.get('client_id', 'unknown_client')
    encoded_crops = data.get('crops', [])
    slots = data.get('slots', [])
    
    decoded_crops = []
    for c in encoded_crops:
        nparr = np.frombuffer(base64.b64decode(c), np.uint8)
        decoded_crops.append(cv2.imdecode(nparr, cv2.IMREAD_COLOR))

    if not decoded_crops:
        return jsonify({"status": "empty"})

    results = model(decoded_crops, conf=0.4, verbose=False)
    resultsBack = modelBack(decoded_crops, conf=DN_CONF_MIN, verbose=False)

    return_detections = []

    if client_id not in player_cards:
        player_cards[client_id] = {}

    all_detections = []
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
    for i, r in enumerate(results):

            slot_data = slots[i]
            rect = slot_data.get('rect', [0, 0, 0, 0])
            label = slot_data.get('label', 'unknown')
            p_idx = slot_data.get('p_idx', 0)
            c_idx = slot_data.get('c_idx', 0)

            roi_x, roi_y, roi_w, roi_h = [int(v) for v in rect]

        
            r_back = resultsBack[i]
            
            if len(r.boxes) > 0:
                for box in r.boxes:
                    lx1, ly1, lx2, ly2 = [int(val) for val in box.xyxy[0]]
                    gx1, gy1, gx2, gy2 = roi_x + lx1, roi_y + ly1, roi_x + lx2, roi_y + ly2

                    conf = box.conf[0].item()
                    card_name = classNames[int(box.cls[0])]
                    return_detections.append({
                                "bbox": [roi_x + lx1, roi_y + ly1, roi_x + lx2, roi_y + ly2],
                                "label": f"{card_name} {conf:.2f}",
                                "color": [0, 0, 255] 
                            })

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
                    if p_idx not in player_cards[client_id]: 
                        player_cards[client_id][p_idx] = {}
                    for idx, card in enumerate(sorted_cards[:2]):
                        player_cards[client_id][p_idx][idx] = {'name': card['name'], 'conf': card['conf'], 'ts': curr_t}
                elif label == "flop":
                    flop_cards[c_idx] = {'name': sorted_cards[0]['name'], 'conf': sorted_cards[0]['conf'], 'ts': curr_t}


            elif len(r_back.boxes) > 0:
                for box_back in r_back.boxes:
                    blx1, bly1, blx2, bly2 = [int(val) for val in box_back.xyxy[0]]
            
                    bgx1 = roi_x + blx1
                    bgy1 = roi_y + bly1
                    bgx2 = roi_x + blx2
                    bgy2 = roi_y + bly2
                    conf = box_back.conf[0].item()

                    if args.verbose:
                        print(f"[VERBOSE] Detected DN in {label} slot {i} (Conf: {conf:.2f})")

                    if label == "player":
                        return_detections.append({
                            "bbox": [roi_x + blx1, roi_y + bly1, roi_x + blx2, roi_y + bly2],
                            "label": f"DN {conf:.2f}",
                            "color": [0, 255, 255] 
                        })

                if label == "player":
                    if p_idx not in player_cards[client_id]: player_cards[client_id][p_idx] = {}
                    for idx in range(min(len(r_back.boxes), 2)):
                        player_cards[client_id][p_idx][idx] = {'name': 'DN', 'conf': r_back.boxes[idx].conf[0].item(), 'ts': curr_t}
                    
    new_player_cards = {}
    for cid, p_data in player_cards.items():
        client_players = {}
        for p_id, cards in p_data.items():
            valid_cards = {c_idx: d for c_idx, d in cards.items() if curr_t - d['ts'] < CARD_TIMEOUT_SECONDS}
            if valid_cards:
                client_players[p_id] = valid_cards
        if client_players:
            new_player_cards[cid] = client_players
    player_cards = new_player_cards

    flop_cards = {c_idx: d for c_idx, d in flop_cards.items() if curr_t - d['ts'] < CARD_TIMEOUT_SECONDS}

    if args.verbose:
        for p_id, cards in player_cards.items():
            for c_idx, data in cards.items():
                if curr_t - data['ts'] >= CARD_TIMEOUT_SECONDS:
                    print(f"[TIMEOUT] Player {p_id+1}, Card Slot {c_idx+1} ({data['name']}) removed after {CARD_TIMEOUT_SECONDS}s")
    if args.verbose:
        for c_idx, data in flop_cards.items():
            if curr_t - data['ts'] >= CARD_TIMEOUT_SECONDS:
                print(f"[TIMEOUT] Flop Slot {c_idx+1} ({data['name']}) removed after {CARD_TIMEOUT_SECONDS}s")



    if args.verbose:
        active_players = [p for p, cards in player_cards.items() if len(cards) > 0]
        active_flop = len(flop_cards)
        print(f"--- Frame Summary ---")
        print(f"Active Players: {active_players} | Cards on Flop: {active_flop}")

        processing_time = (time.time() - curr_t) * 1000
        print(f"Frame Processing Time: {processing_time:.2f}ms")
        
    with open("PokerTracker/data/flop_cards.json", "w") as file:
        json.dump(flop_cards, file, indent=4) 
    file.close()
    with open("PokerTracker/data/player_cards.json", "w") as file:
        json.dump(player_cards, file, indent=4) 
    file.close()

    try:
        calcWinner.evaluate_winner()
    except Exception as e:
        print(f"Calc Winner: An unexpected error occurred: {e}")



    return jsonify({
        "status": "success",
        "detections": return_detections
    })


app.run(host='0.0.0.0', port=5000, debug=False)

from ultralytics import YOLO
import cv2
import math 
import time
import os 
import numpy as np

# --- Configuration Variables ---
X = 1920
Y = 1080

# --- Confidence Boosting Multiplier ---
CONFIDENCE_MULTIPLIER = 0.5 

# --- Timeout Variable (in seconds) ---
CARD_TIMEOUT_SECONDS = 5.0 

# --- Card Image Path Configuration ---
# You MUST place your card images (e.g., 'ace_of_clubs.png') 
# into this folder relative to where you run the script.
CARD_IMAGES_DIR = "card_images"
CARD_IMAGE_WIDTH = 100 # Target width for the displayed cards
CARD_IMAGE_HEIGHT = 140 # Target height for the displayed cards

# start webcam
cap = cv2.VideoCapture(1)
cap.set(3, X)
cap.set(4, Y)

FRAME_WIDTH = int(cap.get(3))
FRAME_HEIGHT = int(cap.get(4))
FRAME_CENTER_Y = FRAME_HEIGHT // 2

# model
model = YOLO("yolov8s_playing_cards.pt")

classNames = [
    '10C', '10D', '10H', '10S', '2C', '2D', '2H', '2S', '3C', '3D', 
    '3H', '3S', '4C', '4D', '4H', '4S', '5C', '5D', '5H', '5S', 
    '6C', '6D', '6H', '6S', '7C', '7D', '7H', '7S', '8C', '8D', 
    '8H', '8S', '9C', '9D', '9H', '9S', 'AC', 'AD', 'AH', 'AS', 
    'JC', 'JD', 'JH', 'JS', 'KC', 'KD', 'KH', 'KS', 'QC', 'QD', 
    'QH', 'QS'
]

# --- Card Name Mapping Helper ---
def get_card_file_name(card_name):
    """Converts a shorthand name (e.g., 'AC') to a file name (e.g., 'ace_of_clubs.png')."""
    rank = card_name[:-1]
    suit = card_name[-1]

    # Map rank
    rank_map = {'A': 'ace', 'K': 'king', 'Q': 'queen', 'J': 'jack', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', '10': '10'}
    if rank == '10': # Handle '10' rank
        rank_full = '10'
    elif rank in rank_map:
        rank_full = rank_map[rank]
    else:
        return None # Invalid rank

    # Map suit
    suit_map = {'C': 'clubs', 'D': 'diamonds', 'H': 'hearts', 'S': 'spades'}
    if suit in suit_map:
        suit_full = suit_map[suit]
    else:
        return None # Invalid suit

    return f"{rank_full}_of_{suit_full}.png"

# --- Image Loading Cache ---
CARD_IMAGE_CACHE = {}

def load_card_image(card_name):
    """Loads and resizes a card image, using a cache to avoid re-reading files."""
    if card_name in CARD_IMAGE_CACHE:
        return CARD_IMAGE_CACHE[card_name]

    file_name = get_card_file_name(card_name)
    if not file_name:
        print(f"Error: Could not map card name {card_name} to a file.")
        return None

    file_path = os.path.join(CARD_IMAGES_DIR, file_name)
    if not os.path.exists(file_path):
        print(f"Error: Card image not found at {file_path}")
        return None

    img = cv2.imread(file_path)
    if img is None:
        print(f"Error: Failed to load image file {file_path}")
        return None
        
    # Resize the image for display
    resized_img = cv2.resize(img, (CARD_IMAGE_WIDTH, CARD_IMAGE_HEIGHT))
    CARD_IMAGE_CACHE[card_name] = resized_img
    
    return resized_img


# --- In-Memory Card Storage Setup (Same as before) ---
player_cards = {} # {card_name: (confidence, timestamp_of_last_update)}
PLAYER_HAND_SIZE = 2 

flop_cards = {} 
FLOP_HAND_SIZE = 3

# Helper function to update the card set (Same as before, returns True if changed)
def update_card_set(card_set, card_name, confidence, max_size):
    current_time = time.time()
    confidence = min(confidence, 1.0) 
    set_changed = False
    
    if card_name in card_set and confidence > card_set[card_name][0]:
        card_set[card_name] = (confidence, current_time)
        set_changed = True
    elif card_name not in card_set and len(card_set) < max_size:
        card_set[card_name] = (confidence, current_time)
        set_changed = True
    elif card_name not in card_set and len(card_set) == max_size:
        lowest_conf_card = None
        lowest_confidence = 1.1 
        
        for name, (conf, timestamp) in card_set.items():
            if conf < lowest_confidence:
                lowest_confidence = conf
                lowest_conf_card = name
        
        if confidence > lowest_confidence:
            del card_set[lowest_conf_card]
            card_set[card_name] = (confidence, current_time)
            set_changed = True

    return set_changed

# Variable to track the last time a card was successfully added/updated in each set
last_player_update_time = time.time()
last_flop_update_time = time.time()


print(f"Frame resolution: {FRAME_WIDTH}x{FRAME_HEIGHT}. Split point Y: {FRAME_CENTER_Y}")

while True:
    current_frame_time = time.time()
    
    success, img = cap.read()
    if not success:
        print("Failed to read frame from webcam.")
        break
    
    # --- Check for Timeout and Clear Structures (Same as before) ---
    latest_player_card_time = max([ts for conf, ts in player_cards.values()] or [last_player_update_time])
    if current_frame_time - latest_player_card_time > CARD_TIMEOUT_SECONDS and player_cards:
        print(f"\nPlayer Hand cleared after {CARD_TIMEOUT_SECONDS}s timeout.")
        player_cards.clear()
        last_player_update_time = current_frame_time 
        
    latest_flop_card_time = max([ts for conf, ts in flop_cards.values()] or [last_flop_update_time])
    if current_frame_time - latest_flop_card_time > CARD_TIMEOUT_SECONDS and flop_cards:
        print(f"\nFlop cleared after {CARD_TIMEOUT_SECONDS}s timeout.")
        flop_cards.clear()
        last_flop_update_time = current_frame_time 

    # --- Temporary Storage for Current Frame Detections ---
    current_frame_detections = {}

    # --- Drawing Split Line for Visualization ---
    cv2.line(img, (0, FRAME_CENTER_Y), (FRAME_WIDTH, FRAME_CENTER_Y), (255, 255, 255), 2)
    cv2.putText(img, "Player Hand (Max 2)", (10, FRAME_CENTER_Y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.putText(img, "Flop (Max 3)", (10, FRAME_CENTER_Y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    results = model(img, stream=True)
    
    player_set_updated_this_frame = False
    flop_set_updated_this_frame = False

    # 1. Collect all detections in the current frame (Draws initial boxes)
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = [int(x) for x in box.xyxy[0]]
            card_center_y = (y1 + y2) // 2
            confidence = box.conf[0].item() 
            cls = int(box.cls[0])
            card_name = classNames[cls]

            position = 'flop' if card_center_y > FRAME_CENTER_Y else 'player'
            box_color = (255, 0, 0) if position == 'flop' else (0, 0, 255) 

            if card_name not in current_frame_detections:
                current_frame_detections[card_name] = {'player': [], 'flop': []}
            
            current_frame_detections[card_name][position].append({'conf': confidence})
            
            # Drawing on Image (initial confidence)
            cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 3)
            text_org = (x1, y1 - 10) 
            cv2.putText(img, f"{card_name} ({confidence:.2f})", text_org, cv2.FONT_HERSHEY_SIMPLEX, 1, box_color, 2)


    # 2. Process collected detections, apply confidence boost, and update permanent sets
    for card_name, positions in current_frame_detections.items():
        for position in ['player', 'flop']:
            detections = positions[position]
            count = len(detections)
            
            if count > 0:
                best_detection = max(detections, key=lambda x: x['conf'])
                initial_conf = best_detection['conf']
                
                # Apply the confidence boosting formula
                boosted_conf = initial_conf * (1 + (count - 1) * CONFIDENCE_MULTIPLIER)
                final_conf_rounded = math.ceil(min(boosted_conf, 1.0) * 100) / 100
                
                # Update the permanent card sets and track if a change occurred
                if position == 'player':
                    if update_card_set(player_cards, card_name, final_conf_rounded, PLAYER_HAND_SIZE):
                        player_set_updated_this_frame = True
                else:
                    if update_card_set(flop_cards, card_name, final_conf_rounded, FLOP_HAND_SIZE):
                        flop_set_updated_this_frame = True

    # 3. Update the last update time if any card was added/changed in this frame
    current_time_for_update = time.time()
    if player_set_updated_this_frame:
        last_player_update_time = current_time_for_update
    if flop_set_updated_this_frame:
        last_flop_update_time = current_time_for_update

    
    # --- Create and Display the New Card View ---
    
    # Determine the size of the new window
    # Player: 2 cards, Flop: 3 cards. Max 5 cards wide.
    # Window Width = (5 * CARD_IMAGE_WIDTH) + (6 * 10px margin)
    DISPLAY_WINDOW_WIDTH = (5 * CARD_IMAGE_WIDTH) + 60 +50
    # Window Height = (2 rows * CARD_IMAGE_HEIGHT) + (3 * 10px margin) + (2 * 30px text height)
    DISPLAY_WINDOW_HEIGHT = (2 * CARD_IMAGE_HEIGHT) + 30 + 60+50
    
    # Create a black canvas for the card display
    display_img = np.zeros((DISPLAY_WINDOW_HEIGHT, DISPLAY_WINDOW_WIDTH, 3), dtype=np.uint8)
    margin = 10
    
    # Draw Player Hand
    cv2.putText(display_img, "PLAYER HAND", (margin, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    x_offset = margin
    y_offset = 30
    
    for card_name, (conf, ts) in player_cards.items():
        card_image = load_card_image(card_name)
        if card_image is not None:
            # Place the card image
            display_img[y_offset:y_offset+CARD_IMAGE_HEIGHT, 
                        x_offset:x_offset+CARD_IMAGE_WIDTH] = card_image
            # Add confidence text below the card
            cv2.putText(display_img, f"{conf:.2f}", (x_offset, y_offset + CARD_IMAGE_HEIGHT + 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            x_offset += CARD_IMAGE_WIDTH + margin

    # Draw Flop
    cv2.putText(display_img, "FLOP", (margin, y_offset + CARD_IMAGE_HEIGHT + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    x_offset = margin
    y_offset = y_offset + CARD_IMAGE_HEIGHT + 50 # New row offset
    
    for card_name, (conf, ts) in flop_cards.items():
        card_image = load_card_image(card_name)
        if card_image is not None:
            # Place the card image
            display_img[y_offset:y_offset+CARD_IMAGE_HEIGHT, 
                        x_offset:x_offset+CARD_IMAGE_WIDTH] = card_image
            # Add confidence text below the card
            cv2.putText(display_img, f"{conf:.2f}", (x_offset, y_offset + CARD_IMAGE_HEIGHT + 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            x_offset += CARD_IMAGE_WIDTH + margin


    # Display the two windows
    cv2.imshow('Webcam - Detection View', img)
    cv2.imshow('Current Hand Display', display_img)
    
    if cv2.waitKey(1) == ord('q'):
        break

# --- Cleanup ---
print("\nDetection stopped. Releasing resources.")
print("\n--- Final Card Data ---")
print(f"Player Cards ({len(player_cards)}/{PLAYER_HAND_SIZE}): {player_cards}")
print(f"Flop Cards ({len(flop_cards)}/{FLOP_HAND_SIZE}): {flop_cards}")

cap.release()
cv2.destroyAllWindows()


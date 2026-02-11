import json
import time
from datetime import datetime
import hashlib



def load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (PermissionError, json.JSONDecodeError, FileNotFoundError):
        return {}
    

state = {
    "last_check_hash": None,
    "current_turn_index": 0,
    "last_round_seen": None,
    "waiting_for_dealer": False,
    "showdown_mode": False,
    "showdown_index": 0
}

def get_file_hash(filename):
    try:
        with open(filename, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except FileNotFoundError:
        return None

def load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def track_poker_turn():
    # 1. Detect Action (Check)
    current_hash = get_file_hash('data/last_check.json')
    new_action = False
    if current_hash and current_hash != state["last_check_hash"]:
        if state["last_check_hash"] is not None:
            new_action = True
        state["last_check_hash"] = current_hash

    # 2. Load Table State
    player_cards = load_json('PokerTracker/data/player_cards.json')
    flop_cards = load_json('PokerTracker/data/flop_cards.json')
    card_count = len(flop_cards)

    # 3. Handle Round Transitions & Reset
    if state["last_round_seen"] != card_count:
        state["current_turn_index"] = 0
        state["last_round_seen"] = card_count
        state["waiting_for_dealer"] = False
        state["showdown_mode"] = False
        state["showdown_index"] = 0
        print(f"--- Street Update: {card_count} cards on board ---")

    # 4. Get Active Players (Still in the hand)
    active_ids = sorted([int(p_id) for p_id, info in player_cards.items() 
                         if info.get("0", {}).get("name") == "DN"])
    
    if not active_ids:
        return {
            "turn": "None",
            "instruction": "WAITING FOR NEW HAND (No active players)",
            "mode": "Idle"
        }

    # 5. Turn and Showdown Logic
    if new_action:
        if state["showdown_mode"]:
            # Progress through the showdown reveal
            state["showdown_index"] += 1
        elif not state["waiting_for_dealer"]:
            # Progress through normal betting/checking
            state["current_turn_index"] += 1
            
            # Check if current street action is finished
            if state["current_turn_index"] >= len(active_ids):
                if card_count >= 5:
                    # If it was the River, go to Showdown
                    state["showdown_mode"] = True
                else:
                    # Otherwise, call for the Dealer
                    state["waiting_for_dealer"] = True

    # 6. Generate Instructions
    if state["showdown_mode"]:
        if state["showdown_index"] < len(active_ids):
            target_player = active_ids[state["showdown_index"]]
            instruction = f"SHOWDOWN: Player {target_player}, REVEAL CARDS"
            current_turn = f"Player {target_player}"
        else:
            instruction = "HAND COMPLETE: Determine Winner"
            current_turn = "None"
    elif state["waiting_for_dealer"]:
        instruction = "!!! DEAL NEXT CARDS !!!"
        current_turn = "Dealer"
    else:
        # Standard Turn
        turn_idx = state["current_turn_index"] % len(active_ids)
        current_player = active_ids[turn_idx]
        instruction = f"Awaiting Action from Player {current_player}"
        current_turn = f"Player {current_player}"

    return {
        "turn": current_turn,
        "instruction": instruction,
        "mode": "Showdown" if state["showdown_mode"] else "Action"
    }

# Main loop
while True:
    res = track_poker_turn()
    print(f"[{res['mode']}] {res['instruction']}")
    time.sleep(0.5)
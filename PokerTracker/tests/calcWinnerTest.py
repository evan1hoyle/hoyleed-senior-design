import json
import os
import unittest
import subprocess
from pathlib import Path

# --- Path Management ---
# Get the directory where calcWinnerTest.py is located
SCRIPT_DIR = Path(__file__).parent.absolute()
# The project root is one level up from tests/
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

FLOP_FILE = DATA_DIR / "flop_cards.json"
PLAYER_FILE = DATA_DIR / "player_cards.json"
WINNER_FILE = DATA_DIR / "winner.json"

DEFAULT_CONF = 0.95
DEFAULT_TS = 1773612816.0

def save_json(filepath, data):
    # Ensure directory exists before saving
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def format_flop(cards):
    return {str(i): {"name": name, "conf": DEFAULT_CONF, "ts": DEFAULT_TS} 
            for i, name in enumerate(cards)}

def format_players(player_data):
    formatted = {}
    for client_id, hands in player_data.items():
        client_dict = {}
        for p_idx, hand in enumerate(hands):
            hand_dict = {}
            for c_idx, card_name in enumerate(hand):
                hand_dict[str(c_idx)] = {
                    "name": card_name,
                    "conf": DEFAULT_CONF,
                    "ts": DEFAULT_TS
                }
            client_dict[str(p_idx)] = hand_dict
        formatted[client_id] = client_dict
    return formatted

class TestPokerWinner(unittest.TestCase):

    def setUp(self):
        """Clean up old winner data before each test."""
        if WINNER_FILE.exists():
            WINNER_FILE.unlink()

    def run_calc_winner(self):
        """Executes calcWinner.py using subprocess."""
        # Point to the script in the project root
        script_path = PROJECT_ROOT / "calcWinner.py"
        # Run it; check=True will raise an error if the script crashes
        subprocess.run(["python3", str(script_path)], check=True, capture_output=True)

    def test_two_pair_vs_high_card(self):
        flop = format_flop(["10S", "6D", "9H", "KH", "2S"])
        players = format_players({
            "585283d0": [["10H", "9D"], ["7C", "5H"]],
            "a90231fb": [["8S", "3D"]]
        })
        save_json(FLOP_FILE, flop)
        save_json(PLAYER_FILE, players)
        
        self.run_calc_winner()
        
        with open(WINNER_FILE, 'r') as f:
            res = json.load(f)
            self.assertEqual(res["winner_id"], "585283d0_0")

    def test_straight_vs_three_of_a_kind(self):
        flop = format_flop(["2S", "3D", "4H", "5S", "JC"])
        players = format_players({
            "client_A": [["6H", "9D"]], 
            "client_B": [["2H", "2D"]]
        })
        save_json(FLOP_FILE, flop)
        save_json(PLAYER_FILE, players)
        
        self.run_calc_winner()
        
        with open(WINNER_FILE, 'r') as f:
            res = json.load(f)
            self.assertEqual(res["winner_id"], "client_A_0")

    def test_full_house_vs_flush(self):
        flop = format_flop(["AS", "AD", "KS", "QS", "2S"])
        players = format_players({
            "player_fh": [["AC", "KH"]], 
            "player_fl": [["JS", "7S"]]
        })
        save_json(FLOP_FILE, flop)
        save_json(PLAYER_FILE, players)
        
        self.run_calc_winner()
        
        with open(WINNER_FILE, 'r') as f:
            res = json.load(f)
            self.assertEqual(res["winner_id"], "player_fh_0")

    def test_split_pot_straights(self):
        """Case: Two players have the exact same 10-high straight."""
        # Board has 6, 7, 8, 9
        flop = format_flop(["6S", "7D", "8H", "9H", "2S"])
        players = format_players({
            "player_one": [["10H", "3D"]], # 6-7-8-9-10 Straight
            "player_two": [["10S", "4C"]]  # 6-7-8-9-10 Straight
        })
        
        save_json(FLOP_FILE, flop)
        save_json(PLAYER_FILE, players)
        
        self.run_calc_winner()
        
        with open(WINNER_FILE, 'r') as f:
            res = json.load(f)
            
            # Validation logic: 
            # If your script returns a single winner_id for ties (e.g., the first one it finds):
            self.assertIn(res["winner_id"], ["player_one_0", "player_two_0"])
            
            # Better check: Both should have the same high score and hand_type
            p1_result = res["results"]["player_one_0"]
            p2_result = res["results"]["player_two_0"]
            
            self.assertEqual(p1_result["hand_type"], "Straight")
            self.assertEqual(p2_result["hand_type"], "Straight")
            self.assertEqual(p1_result["score"], p2_result["score"])
            
            # If your logic marks both as winners:
            self.assertTrue(p1_result["is_winner"])
            self.assertTrue(p2_result["is_winner"])

if __name__ == "__main__":
    unittest.main()
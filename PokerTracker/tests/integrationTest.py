import json
import os
import subprocess
import unittest
import threading
import http.server
import socketserver
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Path setup
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
PORT = 8001  # Using a unique port for integration tests

class PokerIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Start a local HTTP server in a background thread
        os.chdir(PROJECT_ROOT)
        socketserver.TCPServer.allow_reuse_address = True
        handler = http.server.SimpleHTTPRequestHandler
        cls.httpd = socketserver.TCPServer(("", PORT), handler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

        # 2. Configure Selenium
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        cls.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        cls.url = f"http://localhost:{PORT}/index.html"

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'driver'):
            cls.driver.quit()
        if hasattr(cls, 'httpd'):
            cls.httpd.shutdown()
            cls.httpd.server_close()

    def setup_mock_data(self):
        """Sets up the JSON files exactly as seen in your multi-client run."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Flop: 10S, 6D, 9H, KH, 2D
        flop_data = {
            "0": {"name": "10S", "conf": 0.92, "ts": 1773614355.0},
            "1": {"name": "6D", "conf": 0.94, "ts": 1773614355.0},
            "2": {"name": "9H", "conf": 0.93, "ts": 1773614355.0},
            "3": {"name": "KH", "conf": 0.96, "ts": 1773614355.0},
            "4": {"name": "2D", "conf": 0.90, "ts": 1773614355.0}
        }
        
        # Player 0: 9D, 10H (Hits Two Pair)
        # Player 1: 7C, 5H (Hits High Card)
        player_data = {
            "8c7b6705": {
                "0": {
                    "0": {"name": "9D", "conf": 0.90},
                    "1": {"name": "10H", "conf": 0.87}
                },
                "1": {
                    "0": {"name": "7C", "conf": 0.95},
                    "1": {"name": "5H", "conf": 0.90}
                }
            }
        }

        with open(DATA_DIR / "flop_cards.json", 'w') as f:
            json.dump(flop_data, f, indent=4)
        with open(DATA_DIR / "player_cards.json", 'w') as f:
            json.dump(player_data, f, indent=4)
def test_multi_client_scenario(self):
        """End-to-end test for the Player 0 Two-Pair victory (ID Agnostic)."""
        # 1. (Data setup and calcWinner run remains the same...)

        # 2. Backend Verification (winner.json)
        with open(DATA_DIR / "winner.json", 'r') as f:
            win_res = json.load(f)
        
        # Extract whatever dynamic ID was generated
        actual_winner_id = win_res["winner_id"] # e.g., "47928e71_0"
        
        # Verify it's specifically Player 0 who won
        self.assertTrue(actual_winner_id.endswith("_0"), f"Expected Player 0 to win, but got {actual_winner_id}")
        
        # Verify the hand logic is still correct
        winner_data = win_res["results"][actual_winner_id]
        self.assertEqual(winner_data["hand_type"], "Two Pair")
        self.assertTrue(winner_data["is_winner"])

        # 3. Frontend Verification (Browser)
        self.driver.get(self.url)
        wait = WebDriverWait(self.driver, 10)
        
        # Find the box that has the 'winner' class
        winner_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".player-box.winner")))
        
        # Verify the UI shows the correct dynamic ID and hand type
        client_id_prefix = actual_winner_id.split('_')[0]
        self.assertIn(client_id_prefix, winner_box.text)
        self.assertIn("Player 0", winner_box.text)
        
        hand_type_div = winner_box.find_element(By.CLASS_NAME, "hand-type")
        self.assertEqual(hand_type_div.text, "Two Pair")

if __name__ == "__main__":
    unittest.main()
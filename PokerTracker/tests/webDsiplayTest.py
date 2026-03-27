import json
import os
import threading
import http.server
import socketserver
import unittest
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
PORT = 8000

class TestWebDisplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.chdir(PROJECT_ROOT)
        
        # FIX: Allow address reuse to prevent "Address already in use" errors
        socketserver.TCPServer.allow_reuse_address = True
        
        handler = http.server.SimpleHTTPRequestHandler
        cls.httpd = socketserver.TCPServer(("", PORT), handler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

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

    def test_ui_renders_successfully(self):
        """Verify the status light turns green (JS fetch success)."""
        self.driver.get(self.url)
        wait = WebDriverWait(self.driver, 10)
        status_light = wait.until(EC.presence_of_element_located((By.ID, "status-light")))
        
        bg_color = status_light.value_of_css_property("background-color")
        # Accepts both RGB and RGBA formats
        self.assertIn(bg_color, ["rgb(0, 255, 0)", "rgba(0, 255, 0, 1)"])

    def test_kicker_tie_breaker_visual(self):
        """
        Scenario: Both players have a Pair of Aces. 
        Player A has a King kicker, Player B has a Queen kicker.
        """
        # 1. Setup Data
        flop = {
            "0": {"name": "AS", "conf": 0.9, "ts": 1.0},
            "1": {"name": "2D", "conf": 0.9, "ts": 1.0},
            "2": {"name": "5H", "conf": 0.9, "ts": 1.0},
            "3": {"name": "7C", "conf": 0.9, "ts": 1.0},
            "4": {"name": "9S", "conf": 0.9, "ts": 1.0}
        }
        players = {
            "player_A": {"0": {"0": {"name": "AD", "conf": 0.9}, "1": {"name": "KH", "conf": 0.9}}},
            "player_B": {"0": {"0": {"name": "AH", "conf": 0.9}, "1": {"name": "QH", "conf": 0.9}}}
        }
        winner = {
            "winner_id": "player_A_0",
            "results": {
                "player_A_0": {"hand_type": "Pair of Aces, King Kicker", "is_winner": True},
                "player_B_0": {"hand_type": "Pair of Aces, Queen Kicker", "is_winner": False}
            }
        }

        # 2. Write to files
        for filename, content in [("flop_cards.json", flop), ("player_cards.json", players), ("winner.json", winner)]:
            with open(DATA_DIR / filename, 'w') as f:
                json.dump(content, f)

        # 3. Check Browser
        self.driver.get(self.url)
        wait = WebDriverWait(self.driver, 10)
        
        # Verify Player A is highlighted as winner
        winner_box = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "winner")))
        self.assertIn("player_A", winner_box.text)
        
        # Verify the Kicker hand description is visible
        hand_desc = self.driver.find_element(By.CLASS_NAME, "hand-type").text
        self.assertEqual(hand_desc, "Pair of Aces, King Kicker")

if __name__ == "__main__":
    unittest.main()
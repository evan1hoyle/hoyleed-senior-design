import subprocess
import time
import os
import signal
import sys
from pathlib import Path

# Path setup
# SCRIPT_DIR = .../PokerTracker/tests
# PROJECT_ROOT = .../PokerTracker
# TEST_BASE_DIR = .../hoyleed-senior-design (The level where 'PokerTracker/' folder lives)
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
TEST_BASE_DIR = PROJECT_ROOT.parent 

DATA_DIR = PROJECT_ROOT / "data"
VIDEO_PATH = TEST_BASE_DIR / "Testvideo3.mp4"

def run_full_test():
    processes = []
    
    if not VIDEO_PATH.exists():
        print(f"❌ ERROR: Video not found at {VIDEO_PATH}")
        return

    print("🧹 Cleaning up old data...")
    for f in ["player_cards.json", "flop_cards.json", "winner.json"]:
        p = DATA_DIR / f
        if p.exists(): os.remove(p)

    # Environment Setup
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    try:
        print(f"🚀 Starting Server from {TEST_BASE_DIR}...")
        # FIX: We run from TEST_BASE_DIR so that the path 'PokerTracker/models/...' resolves
        server_proc = subprocess.Popen(
            [sys.executable, "PokerTracker/server.py"], 
            cwd=TEST_BASE_DIR,
            env=env
        )
        processes.append(server_proc)
        time.sleep(10) 

        print("🚀 Starting Clients...")
        for zone in ["p_slots_play12", "p_slots_play3"]:
            print(f" -> Launching {zone}")
            proc = subprocess.Popen(
                [sys.executable, "PokerTracker/client.py", "--video", str(VIDEO_PATH), "-pz", zone],
                cwd=TEST_BASE_DIR,
                env=env
            )
            processes.append(proc)

        print("⏳ Polling for results (60s)...")
        start = time.time()
        success = False
        while time.time() - start < 60:
            if (DATA_DIR / "winner.json").exists():
                print(f"✅ Data detected after {int(time.time() - start)}s!")
                time.sleep(2)
                success = True
                break
            time.sleep(2)

        if not success:
            print("❌ TIMEOUT: JSON files never appeared.")
            return

        print("\n🔍 Running Integration UI Tests...")
        # Integration tests usually expect to be in the project root
        subprocess.run([sys.executable, "tests/integrationTest.py"], cwd=PROJECT_ROOT, env=env)

    finally:
        print("\nStopping all processes...")
        for proc in processes:
            try: os.kill(proc.pid, signal.SIGTERM)
            except: pass
        print("Done.")

if __name__ == "__main__":
    run_full_test()
import subprocess
import time
import os
import signal
import sys
from pathlib import Path

# Path Logic
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
TEST_BASE_DIR = PROJECT_ROOT.parent 
DATA_DIR = PROJECT_ROOT / "data"
VIDEO_PATH = TEST_BASE_DIR / "Testvideo3.mp4"

def run_full_test():
    processes = []
    
    # 1. Cleanup
    print("🧹 Cleaning up old JSON data...")
    for f in ["player_cards.json", "flop_cards.json", "winner.json"]:
        p = DATA_DIR / f
        if p.exists(): os.remove(p)

    try:
        # 2. Start the Server (This now starts AI + Web Dashboard)
        print(f"🚀 Starting All-in-One Server from {TEST_BASE_DIR}...")
        server_proc = subprocess.Popen(
            [sys.executable, "PokerTracker/server.py"], 
            cwd=TEST_BASE_DIR
        )
        processes.append(server_proc)
        time.sleep(10) # Give YOLO and Web server time to breathe

        # 3. Start Clients
        for zone in ["p_slots_play12", "p_slots_play3"]:
            print(f" -> Launching Client: {zone}")
            proc = subprocess.Popen(
                [sys.executable, "PokerTracker/client.py", "--video", str(VIDEO_PATH), "-pz", zone],
                cwd=TEST_BASE_DIR
            )
            processes.append(proc)

        # 4. Polling for results
        print("⏳ Processing video frames...")
        start_time = time.time()
        timeout = 60
        while time.time() - start_time < timeout:
            if (DATA_DIR / "winner.json").exists():
                print(f"✅ Data generated in {int(time.time() - start_time)}s")
                time.sleep(3) # Wait for file to fully save
                break
            time.sleep(2)
        else:
            print("❌ TIMEOUT: The system failed to produce winner.json.")
            return

        # 5. Run Integration Test
        print("\n🔍 Verifying UI Dashboard...")
        subprocess.run([sys.executable, "tests/integrationTest.py"], cwd=PROJECT_ROOT)

    finally:
        print("\n🎬 Shutting down system...")
        for proc in processes:
            try: os.kill(proc.pid, signal.SIGTERM)
            except: pass
        print("Done.")

if __name__ == "__main__":
    run_full_test()
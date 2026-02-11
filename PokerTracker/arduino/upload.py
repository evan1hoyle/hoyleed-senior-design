import subprocess

# Configuration
arduino_cli_path = "arduino-cli" 
sketch_path = "/home/evan/projects/hoyleed-senior-design/PokerTracker/arduino"
board_type = "arduino:avr:uno"
port = "/dev/ttyACM0" 

def upload_sketch():
    try:
        print("Compiling...")
        subprocess.run([arduino_cli_path, "compile", "--fqbn", board_type, sketch_path], check=True)
        
        print("Uploading...")
        subprocess.run([arduino_cli_path, "upload", "-p", port, "--fqbn", board_type, sketch_path], check=True)
        
        print("Success!")
    except subprocess.CalledProcessError as e:
        print(f"Deployment failed: {e}")

if __name__ == "__main__":
    upload_sketch()
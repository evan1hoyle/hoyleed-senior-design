import serial
import time
import datetime
import json


arduino_port = "/dev/ttyACM0" 
baud_rate = 9600

try:
    ser = serial.Serial(arduino_port, baud_rate, timeout=1)
    time.sleep(2) 
    print(f"Connected to Arduino on {arduino_port}")

    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').rstrip()
            
            print(f"Arduino: {line}")

            if "Check" in line:
                entry = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "type": "check_event",
                    "data": line.replace("Check:", "").strip()
                }
                with open("../data/last_check.json", "w") as f:
                    f.write(json.dumps(entry) + "\n")
                f.close()
                    
            if "SUCCESS" in line:
                print(">>> Action triggered in Python!")

except KeyboardInterrupt:
    print("\nClosing connection...")
    ser.close()
except Exception as e:
    print(f"Error: {e}")
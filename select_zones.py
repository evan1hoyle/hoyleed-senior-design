import json

def select_zones(cap,cv2,FLOP_HAND_SIZE):
    answer = input("Do you want to draw boxs? (yes/no): ").lower()
    if answer == "yes" or answer == "y":
        f_slots = []
        players = []
        success, frame = cap.read()
        if not success: return [], []
        
        cv2.namedWindow("Setup", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Setup", 1280, 720)

        while True:
            key = cv2.waitKey(0) & 0xFF

            if key == 32:  
                p_slots = []
                roi = cv2.selectROI("Setup", frame, False)
                
                if roi[2] > 0 and roi[3] > 0:
                    p_slots.append(roi)
                    players.append(p_slots)
                    print(f"Added player at {roi}. Press Space for more or Enter to finish.")
                else:
                    print("Selection cancelled.")

            elif key in [13, 10]:  # Enter key
                print("Selection complete.")
                break
                
        for i in range(FLOP_HAND_SIZE):
            print(f"Draw Flop Slot {i+1} and press ENTER")
            roi = cv2.selectROI("Setup", frame, False)
            f_slots.append(roi)
            
        cv2.destroyWindow("Setup")

        with open("data/p_slots.json", "w") as file:
            json.dump(players, file, indent=4) 
        with open("data/f_slots.json", "w") as file:
            json.dump(f_slots, file, indent=4) 

    elif answer == "no" or answer == "n":
        with open("data/p_slots.json", "r") as file:
            players = json.load(file)
        with open("data/f_slots.json", "r") as file:
            f_slots = json.load(file)


    else:
        print("Invalid input. Please enter 'yes' or 'no'.")

    print(players)
    print(f_slots)
    return players, f_slots
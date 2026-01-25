import cv2
import os

# Configuration
image_folder = "/home/evan/hoyleed-senior-design/backCard/images/train"
label_folder = "/home/evan/hoyleed-senior-design/backCard/labels/train"

# Get list of images
images = [f for f in os.listdir(image_folder) if f.endswith(('.jpg', '.png', '.jpeg'))]

for img_name in images:
    img_path = os.path.join(image_folder, img_name)
    label_path = os.path.join(label_folder, os.path.splitext(img_name)[0] + ".txt")

    if not os.path.exists(label_path):
        print(f"No label found for {img_name}, skipping.")
        continue

    img = cv2.imread(img_path)
    h, w, _ = img.shape

    # Read the YOLO format file
    with open(label_path, "r") as f:
        lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        cls_id = parts[0]
        xc, yc, nw, nh = map(float, parts[1:])


        x1 = int((xc - nw / 2) * w)
        y1 = int((yc - nh / 2) * h)
        x2 = int((xc + nw / 2) * w)
        y2 = int((yc + nh / 2) * h)

        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.putText(img, f"Class: {cls_id}", (x1, y1 - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    cv2.imshow("Verification", img)
    
    if cv2.waitKey(0) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
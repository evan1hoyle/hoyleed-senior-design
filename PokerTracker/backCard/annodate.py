import cv2
import os


input_folder = "/home/evan/hoyleed-senior-design/backCard/images/train"      
output_folder = "/home/evan/hoyleed-senior-design/backCard/labels/train"     
class_id = 0                  

if not os.path.exists(output_folder):
    os.makedirs(output_folder)


images = [f for f in os.listdir(input_folder) if f.endswith(('.jpg', '.png', '.jpeg'))]

for img_name in images:
    img_path = os.path.join(input_folder, img_name)
    img = cv2.imread(img_path)
    height, width, _ = img.shape

    roi = cv2.selectROI(f"Annotating: {img_name}", img, fromCenter=False)
    x, y, w, h = roi

    if w > 0 and h > 0:
        x_center = (x + w / 2) / width
        y_center = (y + h / 2) / height
        w_norm = w / width
        h_norm = h / height

        txt_name = os.path.splitext(img_name)[0] + ".txt"
        save_path = os.path.join(output_folder, txt_name)

        with open(save_path, "w") as f:
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}")
        
        print(f"Saved: {txt_name}")
    else:
        print(f"Skipped: {img_name}")

cv2.destroyAllWindows()
print("Done! All images processed.")
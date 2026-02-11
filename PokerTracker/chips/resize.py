import cv2
import os

input_folder = "/home/evan/hoyleed-senior-design/chips/images"
output_folder = "/home/evan/hoyleed-senior-design/chips/images/resized"
target_size = 640  

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

images = [f for f in os.listdir(input_folder) if f.endswith(('.jpg', '.png', '.jpeg'))]

for img_name in images:
    img_path = os.path.join(input_folder, img_name)
    img = cv2.imread(img_path)
    h, w = img.shape[:2]

    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)

    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = cv2.copyMakeBorder(
        resized, 
        0, target_size - new_h,  
        0, target_size - new_w,  
        cv2.BORDER_CONSTANT, 
        value=[0, 0, 0]          
    )

    save_path = os.path.join(output_folder, img_name)
    cv2.imwrite(save_path, canvas)
    print(f"Resized: {img_name} to {target_size}x{target_size}")

print("All images resized successfully!")
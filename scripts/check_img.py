from PIL import Image
import os

img_path = r"c:\Users\ELCOT\Desktop\Unitary X\freelancer\static\img\logo.png"

if os.path.exists(img_path):
    print(f"File exists: {img_path}")
    try:
        with Image.open(img_path) as img:
            print(f"Image Format: {img.format}")
            print(f"Image Size: {img.size}")
            print(f"Image Mode: {img.mode}")
    except Exception as e:
        print(f"Error opening image: {e}")
else:
    print(f"File NOT found: {img_path}")

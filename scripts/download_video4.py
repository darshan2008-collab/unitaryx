import urllib.request
import os

url = "https://raw.githubusercontent.com/rafaelmardojai/rafaelmardojai.github.io/master/assets/video/coding.mp4"
target_path = r"c:\Users\ELCOT\Desktop\Unitary X\freelancer\static\img\login-video.mp4"

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
        out_file.write(response.read())
    print(f"Downloaded successfully. Size: {os.path.getsize(target_path)} bytes")
except Exception as e:
    print("Failed: " + str(e))

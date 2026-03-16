import urllib.request
import os

url = "https://videos.pexels.com/video-files/5453622/5453622-uhd_3840_2160_30fps.mp4"
target_path = r"c:\Users\ELCOT\Desktop\Unitary X\freelancer\static\img\login-video.mp4"

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
try:
    with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
        out_file.write(response.read())
    print(f"Downloaded successfully. Size: {os.path.getsize(target_path)} bytes")
except Exception as e:
    print("Failed: " + str(e))


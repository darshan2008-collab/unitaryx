import urllib.request
import os

url = "https://assets.mixkit.co/videos/preview/mixkit-software-developer-working-on-code-4160-large.mp4"
target_path = r"c:\Users\ELCOT\Desktop\Unitary X\freelancer\static\img\login-video.mp4"

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
        out_file.write(response.read())
    print(f"Downloaded successfully. Size: {os.path.getsize(target_path)} bytes")
except Exception as e:
    print("Failed: " + str(e))

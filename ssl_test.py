import requests

try:
    r = requests.get("https://api.groq.com", timeout=10)
    print("Connected:", r.status_code)
except Exception as e:
    print("Failed:", e)

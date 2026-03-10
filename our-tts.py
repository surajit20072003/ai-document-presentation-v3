import requests
import json

# API Details
URL = "69.197.145.4"
BASE_URL = "http://69.197.145.4:8000"
HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": "c2ef60a22479de3c143851dd9e8808786488928b7bf58c16a8ab92022c568a72"
}

# Data payload
payload = {
    "text": "This is a test using the remote API.", #replace our narration
    "description": "Male speaks clearly with calm tone"
}

# 1. Request the TTS generation
response = requests.post(URL, headers=HEADERS, json=payload)
data = response.json()

if data.get("status") == "success":
    audio_path = data.get("audio_url")
    full_audio_url = f"{BASE_URL}{audio_path}"
    print(f"Audio generated! Downloading from: {full_audio_url}")

    # 2. Download the actual .wav file
    audio_response = requests.get(full_audio_url)
    with open("output_audio.wav", "wb") as f:
        f.write(audio_response.content)
    print("File saved as 'output_audio.wav'")
else:
    print("Error:", data)

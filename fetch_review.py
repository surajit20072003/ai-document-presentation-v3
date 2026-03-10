import requests
import json

url = "http://localhost:5005/job/3407350e/presentation_for_review"
try:
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    # Save formatted JSON to file for reading
    with open("review_response_sample.json", "w") as f:
        json.dump(data, f, indent=2)
        
    print("Response saved to review_response_sample.json")
except Exception as e:
    print(f"Error: {e}")

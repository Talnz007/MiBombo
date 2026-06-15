import base64
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def test_vision():
    test_image = "h:/automatingmework/osint_news_scraper/output/media/twitter_JawadYousufxai_2027037408408023105_1772119908111.png"
    print(f"Loading {test_image}")
    
    with open(test_image, "rb") as f:
        b64_img = base64.b64encode(f.read()).decode("utf-8")
        
    payload = {
        "model": "qwen3-vl:4b",
        "prompt": "What text is in this image? Just give me the text.",
        "stream": False,
        "images": [b64_img]
    }
    
    print("Sending payload...")
    resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code == 200:
        print(f"Response: {resp.json().get('response', '')}")
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    test_vision()

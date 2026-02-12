import requests
import json

def test_chat():
    url = "http://localhost:3000/api/chat"
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Hãy giới thiệu bản thân bạn bằng 1 câu ngắn gọn."
            }
        ]
    }
    
    try:
        print(f"Sending request to {url}...")
        response = requests.post(url, json=payload, stream=True)
        print(f"Status Code: {response.status_code}")
        print("Response Headers:")
        for k, v in response.headers.items():
            print(f"  {k}: {v}")
        
        if response.status_code == 200:
            print("Response stream:")
            for chunk in response.iter_content(chunk_size=None):
                if chunk:
                    print(chunk.decode('utf-8'), end="", flush=True)
            print("\nStream finished.")
        else:
            print(f"Error detail: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {str(e)}")

if __name__ == "__main__":
    test_chat()

import os
import requests
from dotenv import load_dotenv

load_dotenv()

groq_key = os.environ.get("GROQ_API_KEY")
google_key = os.environ.get("GOOGLE_API_KEY")

print(f"Groq key starts with: {groq_key[:5] if groq_key else 'None'}")
print(f"Google key starts with: {google_key[:5] if google_key else 'None'}")

if groq_key:
    models_to_test = ["llama3-8b-8192", "llama3-70b-8192", "llama-3.3-70b-versatile"]
    for model in models_to_test:
        print(f"Testing Groq model: {model}")
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say hi"}],
                    "max_tokens": 50
                }
            )
            print(f"Status: {resp.status_code}")
            if resp.status_code != 200:
                print(resp.text)
        except Exception as e:
            print(e)

if google_key:
    print("Fetching Google models...")
    try:
        resp = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={google_key}")
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            for m in models:
                print(m.get('name'))
        else:
            print(resp.text)
    except Exception as e:
        print(e)

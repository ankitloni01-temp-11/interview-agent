import requests
import json
import time

# Test the LangChain version (we'll start it on port 8001)
URL = "http://localhost:8001/api/chat/11"

messages = [
    "Hi",
    "Let's start the research phase",
    "My GitHub is github.com/priyasharma and LinkedIn is linkedin.com/in/priya-sharma",
    "Okay, let's proceed",
    "I used Docker in a microservices project at my previous company",
    "We had about 15 containers orchestrated with Kubernetes",
    "The main challenge was managing inter-service communication",
]

print("=" * 80)
print("TESTING LANGCHAIN VERSION (Port 8001)")
print("=" * 80)

for i, msg in enumerate(messages, 1):
    print(f"\n[Turn {i}] User: {msg}")
    try:
        response = requests.post(URL, json={"message": msg}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            agent = data.get('agent', 'Unknown')
            resp_text = data.get('response', '')
            print(f"[Agent: {agent}]")
            print(f"Response: {resp_text[:200]}...")
        else:
            print(f"Error: {response.status_code}")
            break
    except Exception as e:
        print(f"Request failed: {e}")
        break
    time.sleep(2)

print("\n" + "=" * 80)
print("LANGCHAIN TEST COMPLETE")
print("=" * 80)

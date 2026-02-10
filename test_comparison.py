import requests
import json
import time

print("=" * 80)
print("SIDE-BY-SIDE INTERVIEW COMPARISON")
print("LangChain (Port 8001) vs LangGraph (Port 8000)")
print("=" * 80)

# First, upload a CV to both servers
print("\n[SETUP] Uploading test CV to both servers...")

cv_file_path = "/home/labuser/VSCODE_training/interview-agent/langchain-interview-agent/resume_priya_sharma.pdf"

# Upload to LangChain (port 8001)
with open(cv_file_path, 'rb') as f:
    files = {'file': ('resume.pdf', f, 'application/pdf')}
    resp1 = requests.post("http://localhost:8001/api/parse-cv", files=files)
    print(f"LangChain CV Upload: {resp1.status_code}")

# Upload to LangGraph (port 8000)
with open(cv_file_path, 'rb') as f:
    files = {'file': ('resume.pdf', f, 'application/pdf')}
    resp2 = requests.post("http://localhost:8000/api/parse-cv", files=files)
    print(f"LangGraph CV Upload: {resp2.status_code}")

time.sleep(2)

# Get CV IDs
cvs_langchain = requests.get("http://localhost:8001/api/cvs").json()
cvs_langgraph = requests.get("http://localhost:8000/api/cvs").json()

cv_id_langchain = cvs_langchain[0]['id'] if cvs_langchain else 1
cv_id_langgraph = cvs_langgraph[0]['id'] if cvs_langgraph else 1

print(f"LangChain CV ID: {cv_id_langchain}")
print(f"LangGraph CV ID: {cv_id_langgraph}")

# Test messages
messages = [
    "Hi",
    "Let's start the research phase",
    "My GitHub is github.com/priyasharma and LinkedIn is linkedin.com/in/priya-sharma",
    "Okay, let's proceed",
]

print("\n" + "=" * 80)
print("RUNNING INTERVIEW TESTS")
print("=" * 80)

for i, msg in enumerate(messages, 1):
    print(f"\n{'='*80}")
    print(f"TURN {i}: {msg}")
    print('='*80)
    
    # Test LangChain
    print("\n[LANGCHAIN]")
    try:
        resp = requests.post(
            f"http://localhost:8001/api/chat/{cv_id_langchain}",
            json={"message": msg},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"Agent: {data.get('agent', 'Unknown')}")
            print(f"Response: {data.get('response', '')[:150]}...")
        else:
            print(f"Error: {resp.status_code}")
    except Exception as e:
        print(f"Failed: {e}")
    
    # Test LangGraph
    print("\n[LANGGRAPH]")
    try:
        resp = requests.post(
            f"http://localhost:8000/api/chat/{cv_id_langgraph}",
            json={"message": msg},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"Agent: {data.get('agent', 'Unknown')}")
            print(f"Response: {data.get('response', '')[:150]}...")
        else:
            print(f"Error: {resp.status_code}")
    except Exception as e:
        print(f"Failed: {e}")
    
    time.sleep(2)

print("\n" + "=" * 80)
print("COMPARISON COMPLETE")
print("=" * 80)

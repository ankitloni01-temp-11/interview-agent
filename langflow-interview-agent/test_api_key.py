import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("GEMINI_API_KEY not found in .env")
    exit(1)

genai.configure(api_key=api_key)

try:
    print(f"Testing key: {api_key[:5]}...{api_key[-5:]}")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hello, are you working?")
    print("Success! Gemini response:")
    print(response.text)
    
    # Test embedding as well since we saw an error in logs
    print("\nTesting embedding model (text-embedding-004)...")
    try:
        embed_res = genai.embed_content(
            model="models/text-embedding-004",
            content="test content"
        )
        print("Embedding Success!")
    except Exception as e:
        print(f"Embedding Failed: {e}")

except Exception as e:
    print(f"Error: {e}")

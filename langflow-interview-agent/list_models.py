import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Listing supported models:")

print("Listing supported models:")
for m in genai.list_models():
    print(f"Model: {m.name}")
    print(f"Methods: {m.supported_generation_methods}")


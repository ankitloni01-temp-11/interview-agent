from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import API_KEY

def get_llm(model_name="gemini-2.0-flash-lite", temperature=0.7):
    """
    Factory method to get a configured ChatGoogleGenerativeAI instance.
    """
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY not found in configuration.")
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=API_KEY,
        temperature=temperature
    )

def get_fast_llm():
    """Returns a lower-temperature Gemini model for extraction/routing."""
    return get_llm(temperature=0.1)

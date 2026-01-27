from typing import Dict, Any, List, Optional
import google.generativeai as genai
import os
from src.config import API_KEY

class BaseAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        if API_KEY:
            genai.configure(api_key=API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    async def process(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes user input with given context.
        Should return a dict with 'response', 'agent' and updated 'context'.
        """
        raise NotImplementedError("Subclasses must implement process()")
    
    def _call_llm(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Helper to call Gemini"""
        if system_instruction:
            model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                system_instruction=system_instruction
            )
        else:
            model = self.model
            
        response = model.generate_content(prompt)
        return response.text.strip()

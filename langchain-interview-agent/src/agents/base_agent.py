from typing import Dict, Any, List, Optional
from src.chain_factory import get_llm
import os

class BaseAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.llm = get_llm()

    async def process(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes user input with given context.
        Should return a dict with 'response', 'agent' and updated 'context'.
        """
        raise NotImplementedError("Subclasses must implement process()")
    
    def _call_llm(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Helper to call Gemini via LangChain"""
        if system_instruction:
            # We can use a prompt template or just a quick system message
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_instruction),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)
        else:
            response = self.llm.invoke(prompt)
            
        return response.content.strip()

from src.agents.base_agent import BaseAgent
from typing import Dict, Any

class GreetingAgent(BaseAgent):
    def __init__(self):
        super().__init__("GreetingBot", "Conversational Greetings and Small Talk")

    async def process(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = """
        You are a friendly Greeting Agent for an Interview System.
        Your job is to respond to greetings (Hi, Hello), small talk (how are you), 
        and closing remarks (bye, thank you).
        Keep it brief and professional. 
        Always remind the user that you are here to help them with the interview process if they seem lost.
        """
        
        response = self._call_llm(user_input, system_instruction=system_prompt)
        
        return {
            "response": response,
            "agent": self.name,
            "context": context
        }

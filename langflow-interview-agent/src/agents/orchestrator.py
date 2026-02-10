from typing import Dict, Any, List
from src.agents.greeting_agent import GreetingAgent
from src.agents.research_agent import ResearchAgent
from src.agents.kpi_agent import KPIAgent
from src.agents.interviewer_agent import InterviewerAgent
from src.agents.feedback_agent import FeedbackAgent

class Orchestrator:
    def __init__(self):
        self.greeting_agent = GreetingAgent()
        self.research_agent = ResearchAgent()
        self.kpi_agent = KPIAgent()
        self.interviewer_agent = InterviewerAgent()
        self.feedback_agent = FeedbackAgent()
        
    async def route(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        state = context.get('state', 'START')
        history = context.get('history', [])
        
        # 1. Handle Greetings (Global) - but skip if links are present
        text = user_input.lower()
        has_links = "github.com" in text or "linkedin.com" in text
        if any(greet in text for greet in ["hi", "hello", "hey"]) and len(history) < 3 and not has_links:
            return await self.greeting_agent.process(user_input, context)

        # 2. State-based routing
        if state == 'START' or state == 'RESEARCH':
            result = await self.research_agent.process(user_input, context)
            if result.get('next_state'):
                context['state'] = result['next_state']
            return result
            
        elif state == 'KPI_CALCULATION':
            result = await self.kpi_agent.process(user_input, context)
            if result.get('next_state'):
                context['state'] = result['next_state']
            return result
            
        elif state == 'INTERVIEW_START' or state == 'INTERVIEWING':
            context['state'] = 'INTERVIEWING'
            # Trigger score after X turns or if user says "finish"
            if "finish the interview" in text or len(history) > 25:
                context['state'] = 'SCORING'
                return await self.feedback_agent.process(user_input, context)
            
            return await self.interviewer_agent.process(user_input, context)
            
        elif state == 'SCORING':
            return await self.feedback_agent.process(user_input, context)

        # Default fallback
        return await self.interviewer_agent.process(user_input, context)

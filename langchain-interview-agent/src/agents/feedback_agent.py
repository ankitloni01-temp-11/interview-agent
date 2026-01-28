from src.agents.base_agent import BaseAgent
from typing import Dict, Any

class FeedbackAgent(BaseAgent):
    def __init__(self):
        super().__init__("ScoreAgent", "Final Assessment and Feedback")

    async def process(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        history = context.get('history', [])
        kpis = context.get('kpis', 'N/A')
        
        # Clean history for prompt
        transcript = "\n".join([f"{m.get('agent', m['role'])}: {m['content']}" for m in history])
        
        system_prompt = f"""
        You are a Senior Hiring Committee Member. 
        Your task is to provide a final, objective assessment of the candidate based on the interview transcript and the defined KPIs.
        
        KPIs to Evaluate:
        {kpis}
        
        Interview Transcript:
        {transcript}
        
        Please provide the assessment in the following format:
        
        ### Overall Score: [X/100]
        [Brief summary of the candidate's performance]
        
        ### KPI Breakdown
        | KPI | Score (1-10) | Evidence / Observations |
        |-----|--------------|-------------------------|
        | [KPI Name] | [Score] | [Short note on what they said/did] |
        ...
        
        ### Recommendation
        [Hire / No Hire / Strong Hire] - [Reasoning]
        
        Be fair but critical. Look for concrete examples provided by the candidate.
        """
        
        evaluation = self._call_llm("Provide final structured score and feedback.", system_instruction=system_prompt)
        
        return {
            "response": f"The interview is now complete. Thank you for your time. Here is my final assessment:\n\n{evaluation}",
            "agent": self.name,
            "context": context,
            "is_final": True
        }

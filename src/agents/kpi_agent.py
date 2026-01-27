from src.agents.base_agent import BaseAgent
from typing import Dict, Any

class KPIAgent(BaseAgent):
    def __init__(self):
        super().__init__("KPIAgent", "Interview KPI Definition and Benchmarking")

    async def process(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        cv_data = context.get('cv_data', {})
        # If the user provides a JD in the input, use it. Otherwise use fallback.
        jd = context.get('job_description')
        if not jd:
            if "junior" in str(cv_data).lower():
                jd = "Junior Software Engineer / AI Enthusiast"
            else:
                jd = "Senior AI and Machine Learning Engineer"
            context['job_description'] = jd

        system_prompt = f"""
        You are an expert HR Specialist and Technical Lead.
        Your task is to define 3-5 specific Key Performance Indicators (KPIs) for an upcoming interview.
        
        Job Description: {jd}
        Candidate Summary: {cv_data.get('profile', 'Expert in their field')}
        Top Skills: {", ".join(cv_data.get('skills', [])[:10])}
        
        For each KPI:
        - Name it clearly (e.g., "Architectural Reasoning", "Python Proficiency").
        - Provide a 1-sentence description of what success looks like.
        - Set a "Benchmark" based on the candidate's seniority (e.g., "Expected: Senior level architectural design").

        Output the KPIs as a clean, numbered list. No extra conversational filler.
        """
        
        kpis = self._call_llm("Generate specific interview KPIs.", system_instruction=system_prompt)
        context['kpis'] = kpis
        
        return {
            "response": f"Based on your profile and the target role ({jd}), I've defined the technical benchmarks for our interview. I'm ready to begin whenever you are. Shall we start?",
            "agent": self.name,
            "context": context,
            "next_state": "INTERVIEW_START"
        }

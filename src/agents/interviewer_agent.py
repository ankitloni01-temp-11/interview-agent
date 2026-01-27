from src.agents.base_agent import BaseAgent
from typing import Dict, Any
import json

class InterviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__("InterviewerAgent", "Conversational Technical Examiner")

    async def process(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        cv_data = context.get('cv_data', {})
        kpis = context.get('kpis', 'General technical proficiency')
        history = context.get('history', [])
        state = context.get('state')
        unverified_skills = context.get('unverified_skills', [])
        discovered_projects = context.get('discovered_projects', [])
        
        # Continuity items
        current_topic = context.get('current_topic')
        covered_topics = context.get('covered_topics', [])
        
        # Turn counters for the 1:2 ratio
        unverified_asked = context.get('unverified_asked', 0)
        projects_asked = context.get('projects_asked', 0)
        
        # Defensive check for discovered_projects to prevent TypeError: string indices must be integers
        project_names_list = []
        for p in discovered_projects:
            if isinstance(p, dict):
                project_names_list.append(p.get('name', 'Unknown Project'))
            elif isinstance(p, str):
                project_names_list.append(p)
        
        system_prompt = f"""
        You are a highly interactive Senior Technical Interviewer.
        
        YOUR MISSION: Maintain a 1:2 ratio of "Unverified Skill Questions" to "Main Project Deep Dives".
        
        CORE RULES:
        1. **Conversational Continuity**: Always acknowledge or briefly critique the candidate's last answer before asking the next question.
        2. **Deep Dives**: If a candidate provides a shallow answer, ask "How specifically?" or "What were the trade-offs?". Do not move to a new topic until you've exhausted the current one.
        3. **Topic Grouping**: Focus on one specific project or one unverified skill at a time. Finish all your questions for that item before moving to the next.
        4. **Explicit Attribution**: When talking about a project, mention it by name: {", ".join(project_names_list) if project_names_list else "the projects on your CV"}.
        5. **No Repetition**: Do not revisit a project or skill you've already thoroughly explored.
        
        Context:
        - Job: {context.get('job_description', 'Technical Role')}
        - KPIs: {kpis}
        - Top CV Skills: {", ".join(cv_data.get('skills', [])[:5])}
        - Verified GitHub Projects: {json.dumps(discovered_projects)}
        
        IMPORTANT: KPIs are internal. Do not name them.
        """
        
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[-8:]])
        
        # Topic selection logic
        if state == 'INTERVIEW_START' or not current_topic:
            context['state'] = 'INTERVIEWING'
            
            # 1:2 Ratio Enforcement
            can_verify = unverified_asked < len(unverified_skills)
            must_do_project = projects_asked < (unverified_asked * 2) or not can_verify
            
            if can_verify and not must_do_project:
                skill = unverified_skills[unverified_asked]
                current_topic = f"Unverified: {skill}"
                prompt = f"Identify that {skill} is on the CV but not GitHub. Ask about their professional implementation of it."
            else:
                # Pick a discovered project or CV project
                available_projects = []
                for p in discovered_projects:
                    name = p.get('name') if isinstance(p, dict) else p
                    if name and name not in covered_topics:
                        available_projects.append(p)

                if available_projects:
                    proj = available_projects[0]
                    p_name = proj.get('name') if isinstance(proj, dict) else proj
                    p_desc = proj.get('description', '') if isinstance(proj, dict) else ''
                    current_topic = f"Project: {p_name}"
                    prompt = f"Pick the project '{p_name}' ({p_desc}). Ask a rigorous architectural question about its core logic or stack choice."
                else:
                    prompt = "Pick a major project from the CV that hasn't been discussed yet. Ask a Level 3 technical question."
            
            context['current_topic'] = current_topic
        else:
            # Continue current topic
            prompt = f"""
            Recent History:
            {history_text}
            
            Current Focus: {current_topic}
            
            Task:
            1. Respond/Critique the last answer.
            2. If '{current_topic}' still has depth, ask a follow-up about architecture or trade-offs.
            3. If exhausted, say "Moving on" and picking a NEW topic based on the 1:2 ratio. 
               (Note: We have currently done {unverified_asked} unverified topics and {projects_asked} projects).
            """

        response = self._call_llm(prompt, system_instruction=system_prompt)
        
        # Update trackers
        if "moving on" in response.lower() or "another area" in response.lower():
            if current_topic:
                covered_topics.append(current_topic.split(': ')[-1])
                if "unverified" in current_topic.lower():
                    unverified_asked += 1
                else:
                    projects_asked += 1
            context['current_topic'] = None
        else:
            context['current_topic'] = current_topic
            
        context['unverified_asked'] = unverified_asked
        context['projects_asked'] = projects_asked
        context['covered_topics'] = covered_topics
        
        return {
            "response": response,
            "agent": self.name,
            "context": context
        }

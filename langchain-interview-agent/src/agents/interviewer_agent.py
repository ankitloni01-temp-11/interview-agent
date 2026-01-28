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
        topic_turns = context.get('topic_turns', 0)
        
        # Turn counters for the 1:2 ratio
        unverified_asked = context.get('unverified_asked', 0)
        projects_asked = context.get('projects_asked', 0)

        system_prompt = f"""
        You are a highly interactive Senior Technical Interviewer.
        
        YOUR MISSION: Maintain a strict 1:2 ratio of "Unverified Skill Questions" to "Main Project Deep Dives".
        
        CORE RULES:
        1. **Conversational Continuity**: Always acknowledge or briefly critique the candidate's last answer before asking the next question.
        2. **Deep Dives**: If a candidate provides a shallow answer, ask "How specifically?" or "What were the trade-offs?". Do not move to a new topic until you've exhausted the current one.
        3. **Topic Grouping**: Focus on one specific project or one unverified skill at a time. Finish all your questions for that item before moving to the next.
        4. **Explicit Attribution**: When talking about a project, mention it by name.
        5. **No Repetition**: Do not revisit a project or skill you've already thoroughly explored. **DO NOT ask about topics listed in 'Topics Already Covered' below.**
        
        Context:
        - Job: {context.get('job_description', 'Technical Role')}
        - KPIs: {kpis}
        - Top CV Skills: {", ".join(cv_data.get('skills', [])[:5])}
        - Verified GitHub Projects: {json.dumps(discovered_projects)}
        - Topics Already Covered: {", ".join(covered_topics) if covered_topics else "None yet"}
        
        IMPORTANT: KPIs are internal. Do not name them.
        """

        # Topic turn management: Increment current turn count if we have a topic
        if current_topic:
            topic_turns += 1
        
        # Internal normalization helper
        def normalize(name):
            return str(name).strip().lower()

        normalized_covered = [normalize(t) for t in covered_topics]
        
        # Detect if the user says "I don't know" or something similar
        input_lower = user_input.lower()
        unknown_signals = [
            "don't know", "do not know", "no idea", "not sure", 
            "don't have experience", "never used", "don't have any experience",
            "basic structure", "don't know much", "just did", "same questions", 
            "skip", "move on", "no experience", "haven't used"
        ]
        is_unknown = any(signal in input_lower for signal in unknown_signals)
        
        # Force transition conditions
        force_transition = False
        if is_unknown and current_topic:
            force_transition = True
        elif current_topic:
            # Turn limits: 2 turns for Unverified Skills (1Q + 1F), 3 turns for Projects (1Q + 2F)
            max_turns = 2 if "unverified" in current_topic.lower() else 3
            if topic_turns > max_turns: # Changed >= to > to allow follow-ups
                force_transition = True
        
        skip_hint = ""
        if force_transition and current_topic:
            topic_name = current_topic.split(': ')[-1]
            print(f"[InterviewerAgent] Transitioning away from '{topic_name}'. Turns: {topic_turns}, Is Unknown: {is_unknown}")
            
            # Mark as covered and increment corresponding counter
            if normalize(topic_name) not in normalized_covered:
                covered_topics.append(topic_name)
                normalized_covered.append(normalize(topic_name))
                if "unverified" in current_topic.lower():
                    unverified_asked += 1
                else:
                    projects_asked += 1
            
            current_topic = None 
            topic_turns = 0
            if is_unknown:
                skip_hint = f"Note: Candidate lacks knowledge for '{topic_name}'. Pivot to a DIFFERENT topic."
            else:
                skip_hint = f"Note: We've covered '{topic_name}' sufficiently. Let's move to a DIFFERENT topic."

        # Topic selection logic
        if state == 'INTERVIEW_START' or not current_topic:
            context['state'] = 'INTERVIEWING'
            topic_turns = 1 # Reset turns for the new topic
            
            # Strict 1:2 Ratio Enforcement (1 Unverified : 2 Projects/Verified)
            can_verify = unverified_asked < len(unverified_skills)
            # Pick Unverified if Projects == Unverified * 2
            pick_unverified = can_verify and (projects_asked == unverified_asked * 2)
            
            if pick_unverified:
                skill = unverified_skills[unverified_asked]
                current_topic = f"Unverified: {skill}"
                prompt = f"I see {skill} is listed on your CV, but I don't see any relevant projects on your GitHub to show your experience. Can you tell me about your professional implementation of it?"
            else:
                # Pick a discovered project
                available_projects = []
                for p in discovered_projects:
                    name = p.get('name') if isinstance(p, dict) else p
                    if name and normalize(name) not in normalized_covered:
                        available_projects.append(p)

                if available_projects:
                    proj = available_projects[0]
                    p_name = proj.get('name') if isinstance(proj, dict) else proj
                    p_desc = proj.get('description', '') if isinstance(proj, dict) else ''
                    current_topic = f"Project: {p_name}"
                    prompt = f"Great, let's dive into your project '{p_name}' ({p_desc}). Ask a rigorous architectural question about its core logic, stack choice, or major trade-offs you faced."
                else:
                    # Fallback to "Verified Skills" (Skills not in unverified_skills)
                    unverified_set = {normalize(s) for s in unverified_skills}
                    verified_skills = [s for s in cv_data.get('skills', []) if normalize(s) not in unverified_set and normalize(s) not in normalized_covered]
                    
                    if verified_skills:
                        skill = verified_skills[0]
                        current_topic = f"Verified Skill: {skill}"
                        prompt = f"Let's discuss your experience with {skill}. Since you've used this in projects found in research, I'd like a deep dive into how you've applied it at scale. What were the biggest technical hurdles?"
                    else:
                        prompt = "Let's explore a major achievement from your employment history. What was the most significant technical challenge you overcame?"
            
            if skip_hint:
                prompt = skip_hint + " " + prompt
                
            context['current_topic'] = current_topic
        else:
            # Continue current topic with deeper follow-up
            prompt = f"The candidate said: '{user_input}'. Acknowledge their response and ask an even DEEPER, more technical follow-up question related to '{current_topic}'. Push for architectural trade-offs or specific edge cases."

        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ]
        
        response_obj = await self.llm.ainvoke(messages)
        response_text = response_obj.content
        
        # Update trackers in context
        context['current_topic'] = current_topic
        context['topic_turns'] = topic_turns
        context['unverified_asked'] = unverified_asked
        context['projects_asked'] = projects_asked
        context['covered_topics'] = covered_topics
        
        return {
            "response": response_text,
            "agent": self.name,
            "context": context
        }

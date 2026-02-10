from src.agents.base_agent import BaseAgent
from typing import Dict, Any, List, Tuple
import json
from src.serper_service import SerperService

class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("ResearchAgent", "Web Verification and Profile Link Discovery")
        self.serper = SerperService()

    async def process(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        cv_data = context.get('cv_data', {})
        if 'contact_information' not in cv_data:
            cv_data['contact_information'] = {}
        contact = cv_data['contact_information']
        
        # Support flat DB schema - migrate flat keys to contact_information if present
        if not contact.get('github') and cv_data.get('github'):
            contact['github'] = cv_data.get('github')
        if not contact.get('linkedin') and cv_data.get('linkedin'):
            contact['linkedin'] = cv_data.get('linkedin')
        if not contact.get('name') and cv_data.get('name'):
            contact['name'] = cv_data.get('name')

        # Current links
        github = contact.get('github') or cv_data.get('github')
        linkedin = contact.get('linkedin') or cv_data.get('linkedin')
        name = contact.get('name', 'candidate')
        
        # Verify existing links if not already verified in this session
        if github and github != "N/A" and not context.get('github_verified'):
            print(f"[ResearchAgent] Proactively verifying GitHub: {github}")
            if self.serper.verify_link(github, name):
                context['github_verified'] = True
            else:
                print(f"[ResearchAgent] GitHub verification failed for {github}")
                # Don't clear it yet, let the missing check handle it if needed
                # or just proceed with warning
        
        if linkedin and linkedin != "N/A" and not context.get('linkedin_verified'):
            print(f"[ResearchAgent] Proactively verifying LinkedIn: {linkedin}")
            if self.serper.verify_link(linkedin, name):
                context['linkedin_verified'] = True
            else:
                print(f"[ResearchAgent] LinkedIn verification failed for {linkedin}")

        input_lower = user_input.lower()
        
        # Check if links are missing OR failed verification
        # (We treat failed verification as missing to prompt the user)
        missing_prompts = []
        if not github or github == "N/A": 
            missing_prompts.append("GitHub")
        elif not context.get('github_verified'):
            missing_prompts.append("Verified GitHub (the one on your CV couldn't be verified)")
            
        if not linkedin or linkedin == "N/A": 
            missing_prompts.append("LinkedIn")
        elif not context.get('linkedin_verified'):
            missing_prompts.append("Verified LinkedIn (the one on your CV couldn't be verified)")

        # Handle "I don't have one"
        if any(phrase in input_lower for phrase in ["don't have", "do not have", "no github", "no linkedin", "skip"]):
            # Fill with placeholder to move past this state
            if not github: contact['github'] = "N/A"
            if not linkedin: contact['linkedin'] = "N/A"
            return {
                "response": "I understand. I'll proceed with the information available on your resume. Let's calculate the interview benchmarks.",
                "agent": self.name,
                "context": context,
                "next_state": "KPI_CALCULATION"
            }

        # If user is providing a link in chat
        if "github.com" in input_lower or "linkedin.com" in input_lower or "http" in input_lower:
            import re
            github_pattern = r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9\._\-/]+'
            linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\._\-/]+'
            
            github_match = re.search(github_pattern, user_input, re.IGNORECASE)
            linkedin_match = re.search(linkedin_pattern, user_input, re.IGNORECASE)
            
            extracted_any = False
            verification_errors = []
            
            if github_match:
                url = github_match.group(0).rstrip('/')
                if not url.startswith('http'): url = 'https://' + url
                if self.serper.verify_link(url, name):
                    contact['github'] = url
                    github = url
                    context['github_verified'] = True
                    extracted_any = True
                else:
                    verification_errors.append(f"GitHub link ({url}) could not be verified for {name}.")

            if linkedin_match:
                url = linkedin_match.group(0).rstrip('/')
                if not url.startswith('http'): url = 'https://' + url
                if self.serper.verify_link(url, name):
                    contact['linkedin'] = url
                    linkedin = url
                    context['linkedin_verified'] = True
                    extracted_any = True
                else:
                    verification_errors.append(f"LinkedIn link ({url}) could not be verified for {name}.")
            
            if verification_errors and not extracted_any:
                return {
                    "response": f"I received the links, but I couldn't verify them as belonging to you: {' '.join(verification_errors)} Could you please provide the correct profile URLs?",
                    "agent": self.name,
                    "context": context
                }

            if extracted_any:
                analysis, unverified, projects = await self._perform_deep_analysis(github, linkedin, cv_data)
                context['unverified_skills'] = unverified
                context['discovered_projects'] = projects
                return {
                    "response": f"Great! I've verified your profiles. {analysis} Let's proceed to the next step.",
                    "agent": self.name,
                    "context": context,
                    "next_state": "KPI_CALCULATION"
                }

        # If we still need links
        if missing_prompts:
            link_str = " and ".join(missing_prompts)
            return {
                "response": f"I've started my research phase, but I notice your {link_str} is missing or could not be verified. Having these allows me to cross-reference your projects for a better interview. Could you please share those URLs?",
                "agent": self.name,
                "context": context
            }
        
        # If links are already present and verified
        analysis, unverified, projects = await self._perform_deep_analysis(github, linkedin, cv_data)
        context['unverified_skills'] = unverified
        context['discovered_projects'] = projects
        return {
            "response": f"I've successfully verified your profiles via web research. {analysis} Based on this, I'll now calculate the Key Performance Indicators for our interview.",
            "agent": self.name,
            "context": context,
            "next_state": "KPI_CALCULATION"
        }

    async def _perform_deep_analysis(self, github: str, linkedin: str, cv_data: Dict) -> Tuple[str, List[str], List[Dict]]:
        """Perform comparison between CV skills and social evidence using LangChain"""
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import JsonOutputParser
        try:
            from langchain_core.pydantic_v1 import BaseModel, Field
        except ImportError:
            try:
                from pydantic.v1 import BaseModel, Field
            except ImportError:
                from pydantic import BaseModel, Field

        name = cv_data.get('contact_information', {}).get('name', 'the candidate')
        skills = cv_data.get('skills', [])
        
        # Real-world verification data
        real_projects = []
        if github and github != "N/A":
            real_projects = self.serper.get_github_repos(github)
        
        projects_text = ""
        if real_projects:
            projects_text = "Discovered GitHub Projects:\n" + "\n".join([f"- {p['name']}: {p['description']}" for p in real_projects])
        else:
            projects_text = "No public GitHub projects found during web research."

        # Define schema for output
        class AnalysisOutput(BaseModel):
            analysis: str = Field(description="A single encouraging sentence for the user about the research.")
            unverified_skills: List[str] = Field(description="A list of 1-3 skills from the CV that seem to lack evidence.")
            discovered_projects: List[Dict] = Field(description="The list of projects found.")

        parser = JsonOutputParser(pydantic_object=AnalysisOutput)

        prompt = ChatPromptTemplate.from_template(
            """
            Candidate: {name}
            Core Skills from CV: {skills}
            GitHub Profile: {github}
            LinkedIn Profile: {linkedin}
            
            {projects_text}
            
            Your task:
            1. Compare the core skills from the CV against the discovered GitHub projects and overall background.
            2. Identify which core skills are NOT easily visible or evidenced as projects on their GitHub/Online presence.
            3. Return your analysis in valid JSON format.
            
            {format_instructions}
            """
        )

        chain = prompt | self.llm | parser

        try:
            data = await chain.ainvoke({
                "name": name,
                "skills": ", ".join(skills),
                "github": github,
                "linkedin": linkedin,
                "projects_text": projects_text,
                "format_instructions": parser.get_format_instructions()
            })
            
            final_projects = data.get("discovered_projects", [])
            
            normalized_projects = []
            for p in final_projects:
                if isinstance(p, dict):
                    normalized_projects.append(p)
                elif isinstance(p, str):
                    normalized_projects.append({"name": p, "description": ""})
            
            if not normalized_projects and real_projects:
                normalized_projects = real_projects

            return data.get("analysis", ""), data.get("unverified_skills", []), normalized_projects
        except Exception as e:
            print(f"Error parsing deep analysis: {e}")
            return "I've analyzed your profiles and am ready to proceed.", [], real_projects

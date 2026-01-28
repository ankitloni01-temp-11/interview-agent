from langchain_core.tools import tool
from src.serper_service import SerperService
from src.database import Database
import json

# Initialize services
serper = SerperService()
# Database will need to be initialized with path, usually handled in app startup
# But for tools we can assume a singleton or pass it in. 
# Here we'll initialize a default one for simplicity in migration.
db = Database()

@tool
def verify_candidate_link(link: str, candidate_name: str) -> bool:
    """
    Verifies if a specific LinkedIn or GitHub link belongs to a candidate.
    Use this when you have a link from a CV and want to confirm it's authentic.
    """
    return serper.verify_link(link, candidate_name)

@tool
def discover_professional_links(candidate_name: str, platform: str = "linkedin") -> str:
    """
    Searches for a candidate's professional profile link (LinkedIn or GitHub) on the web.
    Use this if the profile link is missing or unverified.
    Platform should be 'linkedin' or 'github'.
    """
    return serper.search_profile(candidate_name, platform)

@tool
def fetch_github_repositories(github_url: str) -> str:
    """
    Fetches the names and descriptions of a candidate's public GitHub repositories.
    Use this to gather evidence for technical skills listed on their CV.
    """
    repos = serper.get_github_repos(github_url)
    return json.dumps(repos)

@tool
def get_cv_details(cv_id: int) -> str:
    """
    Retrieves the full parsed data of a candidate's CV from the database using their ID.
    Includes skills, employment history, and education.
    """
    cv_data = db.get_cv_by_id(cv_id)
    if not cv_data:
        return "CV not found."
    return json.dumps(cv_data)

# Export a list of all tools
ALL_TOOLS = [
    verify_candidate_link, 
    discover_professional_links, 
    fetch_github_repositories,
    get_cv_details
]

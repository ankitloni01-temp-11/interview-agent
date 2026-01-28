import requests
import json
from src.config import SERPER_API_KEY

class SerperService:
    def __init__(self):
        self.api_key = SERPER_API_KEY
        self.url = "https://google.serper.dev/search"

    def search_profile(self, name, platform="linkedin"):
        """
        Search for a professional profile on a specific platform.
        """
        if not self.api_key:
            print(f"[Serper] Warning: No API key configured. Skipping search for {platform}.")
            return None

        query = f"{name} {platform} profile"
        payload = json.dumps({
            "q": query,
            "num": 3
        })
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            print(f"[Serper] Searching for {platform} profile for: {name}")
            response = requests.request("POST", self.url, headers=headers, data=payload)
            results = response.json()

            if "organic" in results:
                for result in results["organic"]:
                    link = result.get("link", "")
                    # Basic validation/filtering for the platform
                    if platform.lower() in link.lower():
                        print(f"[Serper] Found {platform} link: {link}")
                        return link
            
            print(f"[Serper] No {platform} profile found for: {name}")
            return None
        except Exception as e:
            print(f"[Serper] Error during search: {e}")
            return None

    def verify_link(self, link, name):
        """
        Verify if a given link belongs to the candidate with the provided name.
        Uses Serper to search for the link and checks if the name appears in results.
        """
        if not self.api_key or not link or not name:
            return False

        # Query for the specific link to see how Google indexes it
        # We search for the link itself to get the snippet/title
        query = f'link:"{link}"'
        payload = json.dumps({
            "q": query,
            "num": 1
        })
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            print(f"[Serper] Verifying link {link} for candidate: {name}")
            response = requests.request("POST", self.url, headers=headers, data=payload)
            results = response.json()

            if "organic" in results:
                for result in results["organic"]:
                    title = result.get("title", "").lower()
                    snippet = result.get("snippet", "").lower()
                    name_parts = name.lower().split()
                    
                    # Check if all parts of the name (or at least first and last) appear in title/snippet
                    matches = sum(1 for part in name_parts if part in title or part in snippet)
                    if matches >= min(2, len(name_parts)):
                        print(f"[Serper] Verification SUCCESS for {link}")
                        return True
            
            # Fallback search: name + "site:domain"
            domain = "linkedin.com" if "linkedin.com" in link else "github.com"
            query_fallback = f'"{name}" site:{domain}'
            payload_fallback = json.dumps({
                "q": query_fallback,
                "num": 3
            })
            
            response_fb = requests.request("POST", self.url, headers=headers, data=payload_fallback)
            results_fb = response_fb.json()
            
            if "organic" in results_fb:
                for result in results_fb["organic"]:
                    found_link = result.get("link", "")
                    if link.split('?')[0].rstrip('/') in found_link or found_link in link:
                        print(f"[Serper] Verification SUCCESS (fallback search) for {link}")
                        return True

            print(f"[Serper] Verification FAILED for {link}")
            return False
        except Exception as e:
            print(f"[Serper] Error during verification: {e}")
            return False

    def get_github_repos(self, github_url):
        """
        Search for repositories on a GitHub profile.
        """
        if not self.api_key or not github_url:
            return []

        username = github_url.split('/')[-1]
        query = f'site:github.com "{username}" repositories'
        payload = json.dumps({
            "q": query,
            "num": 5
        })
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            print(f"[Serper] Fetching repos for: {username}")
            response = requests.request("POST", self.url, headers=headers, data=payload)
            results = response.json()
            repos = []

            if "organic" in results:
                for result in results["organic"]:
                    title = result.get("title", "")
                    link = result.get("link", "")
                    snippet = result.get("snippet", "")
                    
                    # Try to extract repo name from title (usually "username/reponame")
                    if "/" in title and username.lower() in title.lower():
                        repo_name = title.split()[0] # Simplistic extraction
                        if "/" in repo_name:
                            repos.append({"name": repo_name, "description": snippet})
            
            return repos[:3]
        except Exception as e:
            print(f"[Serper] Error fetching repos: {e}")
            return []

    def find_links(self, name):
        """
        Find both LinkedIn and GitHub links for a name.
        """
        if not name:
            return {}

        links = {}
        
        linkedin = self.search_profile(name, "linkedin")
        if linkedin:
            links["linkedin"] = linkedin
            
        github = self.search_profile(name, "github")
        if github:
            links["github"] = github
            
        return links

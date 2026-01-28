import google.generativeai as genai
import PyPDF2
import json
from src.config import API_KEY
from src.serper_service import SerperService

class GeminiParser:
    def __init__(self):
        if not API_KEY:
            raise ValueError("API key is required")
        genai.configure(api_key=API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.serper = SerperService()

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        import io
        text = ""
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    def parse_cv(self, pdf_content: bytes) -> dict:
        cv_text = self.extract_text_from_pdf(pdf_content)
        if not cv_text:
            return {"error": "Could not extract text from CV"}

        prompt = f"""Analyze the following resume and extract all information in JSON format.
Be extremely thorough and extract all available information, especially social media and portfolio links.

Resume Text:
{cv_text}

Search for URLs and social media profiles even if they are not explicitly labeled. 
Look for patterns like:
- github.com/username
- linkedin.com/in/username
- twitter.com/username (if relevant)
- personal websites (e.g., username.github.io, portfolio.com)

Even if the "https://" part is missing (e.g., "linkedin.com/in/arjunmehta"), you MUST extract it and convert it to a full URL (e.g., "https://linkedin.com/in/arjunmehta").

Return the extracted information as valid JSON with this exact structure:
{{
    "contact_information": {{
        "name": "string or null",
        "email": "string or null",
        "phone": "string or null",
        "address": "string or null",
        "linkedin": "string or null",
        "github": "string or null"
    }},
    "profile": "string or null",
    "employment_history": [
        {{
            "title": "string",
            "company": "string",
            "location": "string or null",
            "start_date": "string or null",
            "end_date": "string or null",
            "description": "string or null",
            "achievements": ["string"]
        }}
    ],
    "education": [
        {{
            "degree": "string",
            "institution": "string",
            "location": "string or null",
            "start_date": "string or null",
            "end_date": "string or null",
            "majors": ["string"],
            "minors": ["string"]
        }}
    ],
    "skills": ["string"],
    "certifications": ["string"],
    "licenses": ["string"],
    "languages": ["string"],
    "achievements": ["string"],
    "hobbies": ["string"]
}}

Return ONLY the JSON, no markdown or extra text. Ensure all URLs are absolute (e.g., https://github.com/...) if possible."""

        try:
            response = self.model.generate_content(prompt)
            try:
                cleaned_text = response.text.strip()
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text.split("```")[1]
                    if cleaned_text.startswith("json"):
                        cleaned_text = cleaned_text[4:]
                cleaned_text = cleaned_text.strip()
                parsed_data = json.loads(cleaned_text)
                
                # --- Regex-based Fallback for Links ---
                if "contact_information" not in parsed_data:
                    parsed_data["contact_information"] = {}
                
                contact = parsed_data["contact_information"]
                
                import re
                
                # LinkedIn Regex
                if not contact.get("linkedin"):
                    li_match = re.search(r'(?:linkedin\.com/in/)([a-zA-Z0-9\-\_]+)', cv_text)
                    if li_match:
                        contact["linkedin"] = f"https://www.linkedin.com/in/{li_match.group(1)}"
                        print(f"[GeminiParser] Found LinkedIn via regex: {contact['linkedin']}")
                
                # GitHub Regex
                if not contact.get("github"):
                    gh_match = re.search(r'(?:github\.com/)([a-zA-Z0-9\-\_]+)', cv_text)
                    if gh_match:
                        contact["github"] = f"https://github.com/{gh_match.group(1)}"
                        print(f"[GeminiParser] Found GitHub via regex: {contact['github']}")
                
                # --- Link Verification and Fallback ---
                contact = parsed_data.get("contact_information", {})
                name = contact.get("name")
                
                if name:
                    # Validate existing LinkedIn
                    if contact.get("linkedin"):
                        print(f"[GeminiParser] Verifying extracted LinkedIn: {contact['linkedin']}")
                        is_valid = self.serper.verify_link(contact["linkedin"], name)
                        if not is_valid:
                            print(f"[GeminiParser] Extracted LinkedIn failed verification. Searching for correct one...")
                            found_linkedin = self.serper.search_profile(name, "linkedin")
                            if found_linkedin:
                                contact["linkedin"] = found_linkedin
                            else:
                                contact["linkedin_verified"] = False
                        else:
                            contact["linkedin_verified"] = True
                    else:
                        # Fallback if missing
                        print(f"[GeminiParser] LinkedIn missing for {name}, trying Serper...")
                        found_linkedin = self.serper.search_profile(name, "linkedin")
                        if found_linkedin:
                            contact["linkedin"] = found_linkedin
                            contact["linkedin_verified"] = True
                    
                    # Validate existing GitHub
                    if contact.get("github"):
                        print(f"[GeminiParser] Verifying extracted GitHub: {contact['github']}")
                        is_valid = self.serper.verify_link(contact["github"], name)
                        if not is_valid:
                            print(f"[GeminiParser] Extracted GitHub failed verification. Searching for correct one...")
                            found_github = self.serper.search_profile(name, "github")
                            if found_github:
                                contact["github"] = found_github
                            else:
                                contact["github_verified"] = False
                        else:
                            contact["github_verified"] = True
                    else:
                        # Fallback if missing
                        print(f"[GeminiParser] GitHub missing for {name}, trying Serper...")
                        found_github = self.serper.search_profile(name, "github")
                        if found_github:
                            contact["github"] = found_github
                            contact["github_verified"] = True
                            
                    parsed_data["contact_information"] = contact
                # ------------------------------------

                return parsed_data
            except json.JSONDecodeError as e:
                return {"error": f"Failed to parse JSON response: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}

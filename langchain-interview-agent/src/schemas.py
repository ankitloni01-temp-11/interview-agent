from pydantic import BaseModel
from typing import List, Optional

class ContactInformation(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None

class EmploymentHistory(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    achievements: List[str] = []

class Education(BaseModel):
    degree: str
    institution: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    majors: List[str] = []

class CVData(BaseModel):
    contact_information: ContactInformation
    profile: Optional[str] = None
    employment_history: List[EmploymentHistory] = []
    education: List[Education] = []
    skills: List[str] = []
    certifications: List[str] = []
    languages: List[str] = []

class CVResponse(BaseModel):
    id: int
    name: str
    email: str
    filename: str
    created_at: str

    class Config:
        from_attributes = True

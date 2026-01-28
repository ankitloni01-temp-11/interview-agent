"""
Vector Store module for RAG-based schema retrieval.
Uses ChromaDB with Google's text-embedding-004 model.
"""

import chromadb
from chromadb.config import Settings
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import json
import os

from src.config import API_KEY


class GoogleEmbeddingFunction:
    """Custom embedding function using Google's text-embedding-004"""
    
    def __init__(self):
        if not API_KEY:
            raise ValueError("GEMINI_API_KEY required for embeddings")
        genai.configure(api_key=API_KEY)
        self.model_name = "models/text-embedding-004"
    
    def name(self) -> str:
        """Return the name of the embedding function (required by ChromaDB)"""
        return "google-text-embedding-004"
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        embeddings = []
        for text in input:
            result = genai.embed_content(
                model=self.model_name,
                content=text
            )
            embeddings.append(result['embedding'])
        return embeddings


class SchemaVectorStore:
    """
    Vector store for CV database schema using ChromaDB.
    Implements table-level chunking strategy.
    """
    
    def __init__(self, persist_directory: str = "data/chroma_db"):
        """Initialize ChromaDB with persistent storage"""
        self.persist_directory = persist_directory
        
        # Create directory if not exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Initialize embedding function
        self.embedding_fn = GoogleEmbeddingFunction()
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="cv_schema",
            embedding_function=self.embedding_fn,
            metadata={"description": "CV database schema and context"}
        )
        
        print(f"[VectorStore] Initialized at {persist_directory}")
        
        # Index schema chunks if collection is empty
        if self.collection.count() == 0:
            self._index_schema_chunks()
    
    def _create_schema_chunks(self) -> List[Dict[str, Any]]:
        """
        Create table-level chunks for the database schema.
        Each chunk contains: table info, columns, relationships, query patterns.
        """
        chunks = [
            {
                "id": "table_resumes",
                "content": """TABLE: resumes
PURPOSE: Main table storing parsed CV/resume information for each candidate.

COLUMNS:
- id (INTEGER PRIMARY KEY): Unique identifier for each resume
- filename (TEXT): Original PDF filename
- name (TEXT): Candidate's full name
- email (TEXT): Candidate's email address
- phone (TEXT): Phone number
- address (TEXT): Physical address
- linkedin (TEXT): LinkedIn profile URL
- github (TEXT): GitHub profile URL
- profile (TEXT): Professional summary/profile text
- raw_data (TEXT): Original JSON parsed data
- created_at (TIMESTAMP): When the resume was added

RELATIONSHIPS:
- One-to-many with skills (skills.resume_id → resumes.id)
- One-to-many with employment_history
- One-to-many with education
- One-to-many with certifications
- One-to-many with languages

COMMON QUERIES:
- Get all resumes: SELECT * FROM resumes ORDER BY created_at DESC
- Count resumes: SELECT COUNT(*) FROM resumes
- Find by name: SELECT * FROM resumes WHERE name LIKE '%search%'
- Find by email: SELECT * FROM resumes WHERE email = 'email@example.com'""",
                "metadata": {"table": "resumes", "type": "schema", "category": "main"}
            },
            {
                "id": "table_skills",
                "content": """TABLE: skills
PURPOSE: Stores individual skills for each resume (normalized, one skill per row).

COLUMNS:
- id (INTEGER PRIMARY KEY): Unique skill entry ID
- resume_id (INTEGER FK): Links to resumes.id
- skill_name (TEXT): Name of the skill (e.g., "Python", "Machine Learning")
- created_at (TIMESTAMP): When added

RELATIONSHIPS:
- Many-to-one with resumes (skills.resume_id → resumes.id)
- CASCADE DELETE: Skills deleted when parent resume deleted

COMMON QUERIES:
- All unique skills: SELECT DISTINCT skill_name FROM skills ORDER BY skill_name
- Count unique skills: SELECT COUNT(DISTINCT skill_name) FROM skills
- Skills for a person: SELECT skill_name FROM skills WHERE resume_id = ?
- Find people with skill: SELECT r.name FROM resumes r JOIN skills s ON r.id = s.resume_id WHERE s.skill_name LIKE '%Python%'
- Most common skills: SELECT skill_name, COUNT(*) as count FROM skills GROUP BY skill_name ORDER BY count DESC
- Person with most skills: SELECT r.name, COUNT(s.id) as skill_count FROM resumes r LEFT JOIN skills s ON r.id = s.resume_id GROUP BY r.id ORDER BY skill_count DESC LIMIT 1""",
                "metadata": {"table": "skills", "type": "schema", "category": "attributes"}
            },
            {
                "id": "table_employment",
                "content": """TABLE: employment_history
PURPOSE: Stores work experience entries for each resume.

COLUMNS:
- id (INTEGER PRIMARY KEY): Unique entry ID
- resume_id (INTEGER FK): Links to resumes.id
- job_title (TEXT): Position/role title
- company_name (TEXT): Employer/company name
- location (TEXT): Job location
- start_date (TEXT): Employment start date
- end_date (TEXT): Employment end date (may be "Present")
- description (TEXT): Job responsibilities and achievements
- created_at (TIMESTAMP): When added

RELATIONSHIPS:
- Many-to-one with resumes (employment_history.resume_id → resumes.id)

COMMON QUERIES:
- All companies: SELECT DISTINCT company_name FROM employment_history WHERE company_name IS NOT NULL ORDER BY company_name
- All job titles: SELECT DISTINCT job_title FROM employment_history ORDER BY job_title
- Work history for person: SELECT job_title, company_name, start_date, end_date FROM employment_history WHERE resume_id = ?
- People who worked at company: SELECT r.name, e.job_title FROM resumes r JOIN employment_history e ON r.id = e.resume_id WHERE e.company_name LIKE '%Google%'
- Count jobs per person: SELECT r.name, COUNT(e.id) as job_count FROM resumes r LEFT JOIN employment_history e ON r.id = e.resume_id GROUP BY r.id""",
                "metadata": {"table": "employment_history", "type": "schema", "category": "experience"}
            },
            {
                "id": "table_education",
                "content": """TABLE: education
PURPOSE: Stores educational background for each resume.

COLUMNS:
- id (INTEGER PRIMARY KEY): Unique entry ID
- resume_id (INTEGER FK): Links to resumes.id
- degree (TEXT): Degree name (e.g., "Bachelor of Science", "MBA")
- institution (TEXT): School/university name
- location (TEXT): Institution location
- start_date (TEXT): Start date
- end_date (TEXT): Graduation/end date
- created_at (TIMESTAMP): When added

RELATIONSHIPS:
- Many-to-one with resumes (education.resume_id → resumes.id)

COMMON QUERIES:
- All institutions: SELECT DISTINCT institution FROM education ORDER BY institution
- All degrees: SELECT DISTINCT degree FROM education ORDER BY degree
- Education for person: SELECT degree, institution, end_date FROM education WHERE resume_id = ?
- People from university: SELECT r.name, e.degree FROM resumes r JOIN education e ON r.id = e.resume_id WHERE e.institution LIKE '%MIT%'
- Count by degree type: SELECT degree, COUNT(*) as count FROM education GROUP BY degree ORDER BY count DESC""",
                "metadata": {"table": "education", "type": "schema", "category": "education"}
            },
            {
                "id": "table_certifications",
                "content": """TABLE: certifications
PURPOSE: Stores professional certifications for each resume.

COLUMNS:
- id (INTEGER PRIMARY KEY): Unique entry ID
- resume_id (INTEGER FK): Links to resumes.id
- certification_name (TEXT): Name of certification (e.g., "AWS Certified", "PMP")
- created_at (TIMESTAMP): When added

RELATIONSHIPS:
- Many-to-one with resumes (certifications.resume_id → resumes.id)

COMMON QUERIES:
- All certifications: SELECT DISTINCT certification_name FROM certifications ORDER BY certification_name
- Count certifications: SELECT COUNT(DISTINCT certification_name) FROM certifications
- Certifications for person: SELECT certification_name FROM certifications WHERE resume_id = ?
- People with certification: SELECT r.name FROM resumes r JOIN certifications c ON r.id = c.resume_id WHERE c.certification_name LIKE '%AWS%'
- Most common certifications: SELECT certification_name, COUNT(*) as count FROM certifications GROUP BY certification_name ORDER BY count DESC""",
                "metadata": {"table": "certifications", "type": "schema", "category": "credentials"}
            },
            {
                "id": "table_languages",
                "content": """TABLE: languages
PURPOSE: Stores language proficiencies for each resume.

COLUMNS:
- id (INTEGER PRIMARY KEY): Unique entry ID
- resume_id (INTEGER FK): Links to resumes.id
- language_name (TEXT): Language name (e.g., "English", "Spanish", "Mandarin")
- created_at (TIMESTAMP): When added

RELATIONSHIPS:
- Many-to-one with resumes (languages.resume_id → resumes.id)

COMMON QUERIES:
- All languages: SELECT DISTINCT language_name FROM languages ORDER BY language_name
- Count languages: SELECT COUNT(DISTINCT language_name) FROM languages
- Languages for person: SELECT language_name FROM languages WHERE resume_id = ?
- People speaking language: SELECT r.name FROM resumes r JOIN languages l ON r.id = l.resume_id WHERE l.language_name LIKE '%Spanish%'
- Most common languages: SELECT language_name, COUNT(*) as count FROM languages GROUP BY language_name ORDER BY count DESC""",
                "metadata": {"table": "languages", "type": "schema", "category": "attributes"}
            },
            {
                "id": "relationships_overview",
                "content": """DATABASE RELATIONSHIPS OVERVIEW

The CV database uses a normalized schema with the following structure:

MAIN TABLE:
- resumes: Central table holding candidate information

RELATED TABLES (all linked via resume_id foreign key):
- skills: Technical and soft skills (many per resume)
- employment_history: Work experience entries (many per resume)
- education: Academic background (many per resume)
- certifications: Professional certifications (many per resume)
- languages: Language proficiencies (many per resume)

JOIN PATTERNS:
1. Simple join to get related data:
   SELECT r.name, s.skill_name 
   FROM resumes r 
   JOIN skills s ON r.id = s.resume_id

2. Count related items:
   SELECT r.name, COUNT(s.id) as skill_count 
   FROM resumes r 
   LEFT JOIN skills s ON r.id = s.resume_id 
   GROUP BY r.id

3. Filter by related data:
   SELECT DISTINCT r.* 
   FROM resumes r 
   JOIN skills s ON r.id = s.resume_id 
   WHERE s.skill_name LIKE '%Python%'

4. Multiple table joins:
   SELECT r.name, s.skill_name, e.company_name
   FROM resumes r
   LEFT JOIN skills s ON r.id = s.resume_id
   LEFT JOIN employment_history e ON r.id = e.resume_id

IMPORTANT: Always use LEFT JOIN when counting to include resumes with zero related items.""",
                "metadata": {"table": "all", "type": "relationships", "category": "overview"}
            },
            {
                "id": "sql_patterns",
                "content": """COMMON SQL PATTERNS FOR CV DATABASE

COUNTING:
- Total resumes: SELECT COUNT(*) as total FROM resumes
- Unique skills: SELECT COUNT(DISTINCT skill_name) FROM skills
- Items per person: SELECT r.name, COUNT(s.id) FROM resumes r LEFT JOIN skills s ON r.id = s.resume_id GROUP BY r.id

AGGREGATIONS:
- Most skills: ORDER BY skill_count DESC LIMIT 1
- Top N items: LIMIT N
- Group by category: GROUP BY column_name

SEARCHING:
- Partial match: WHERE column LIKE '%term%'
- Exact match: WHERE column = 'value'
- Case insensitive: WHERE LOWER(column) LIKE LOWER('%term%')

SORTING:
- Alphabetical: ORDER BY column ASC
- Newest first: ORDER BY created_at DESC
- By count: ORDER BY COUNT(*) DESC

NULL HANDLING:
- Exclude nulls: WHERE column IS NOT NULL
- Include check: COALESCE(column, 'default')

DISTINCT:
- Unique values: SELECT DISTINCT column FROM table
- Unique combinations: SELECT DISTINCT col1, col2 FROM table""",
                "metadata": {"table": "all", "type": "patterns", "category": "queries"}
            }
        ]
        
        return chunks
    
    def _index_schema_chunks(self):
        """Index all schema chunks into ChromaDB"""
        chunks = self._create_schema_chunks()
        
        ids = [chunk["id"] for chunk in chunks]
        documents = [chunk["content"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        print(f"[VectorStore] Indexed {len(chunks)} schema chunks")
    
    def add_resume_context(self, resume_id: int, resume_data: Dict) -> bool:
        """
        Add resume-specific context when a new resume is uploaded.
        This enriches the vector store with candidate-specific information.
        """
        try:
            name = resume_data.get('contact_information', {}).get('name', 'Unknown')
            skills = resume_data.get('skills', [])
            employment = resume_data.get('employment_history', [])
            education = resume_data.get('education', [])
            
            # Create a summary document for this resume
            skills_text = ", ".join(skills[:10]) if skills else "No skills listed"
            companies = [job.get('company', '') for job in employment if job.get('company')]
            companies_text = ", ".join(companies[:5]) if companies else "No companies listed"
            
            # Safe name handling
            display_name = name if name else "Unknown Candidate"
            
            content = f"""RESUME: {display_name} (ID: {resume_id})
SKILLS: {skills_text}
COMPANIES: {companies_text}
SKILL COUNT: {len(skills)}
JOB COUNT: {len(employment)}
EDUCATION COUNT: {len(education)}

This resume can be queried using:
- Skills: SELECT skill_name FROM skills WHERE resume_id = {resume_id}
- Employment: SELECT * FROM employment_history WHERE resume_id = {resume_id}
- Find this person: SELECT * FROM resumes WHERE id = {resume_id}
- Find by name: SELECT * FROM resumes WHERE name LIKE '%{display_name.split()[0]}%'"""
            
            self.collection.upsert(
                ids=[f"resume_{resume_id}"],
                documents=[content],
                metadatas=[{
                    "table": "resumes",
                    "type": "resume_context",
                    "resume_id": str(resume_id),
                    "name": name
                }]
            )
            
            print(f"[VectorStore] Added context for resume {resume_id}: {name}")
            return True
            
        except Exception as e:
            print(f"[VectorStore ERROR] Failed to add resume context: {e}")
            return False
    
    def remove_resume_context(self, resume_id: int) -> bool:
        """Remove resume context when a resume is deleted"""
        try:
            self.collection.delete(ids=[f"resume_{resume_id}"])
            print(f"[VectorStore] Removed context for resume {resume_id}")
            return True
        except Exception as e:
            print(f"[VectorStore ERROR] Failed to remove resume context: {e}")
            return False
    
    def get_relevant_context(self, query: str, k: int = 3) -> str:
        """
        Retrieve top-k relevant schema chunks for a user query.
        Returns formatted context string for the LLM prompt.
        """
        try:
            # Generate query embedding manually
            query_embedding = self.embedding_fn([query])[0]
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas"]
            )
            
            if not results or not results['documents'] or not results['documents'][0]:
                print("[VectorStore] No relevant chunks found, using default schema")
                return self._get_default_schema()
            
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            
            # Build context from retrieved chunks
            context_parts = []
            for doc, meta in zip(documents, metadatas):
                table = meta.get('table', 'unknown')
                chunk_type = meta.get('type', 'schema')
                context_parts.append(f"--- {table.upper()} ({chunk_type}) ---\n{doc}")
            
            context = "\n\n".join(context_parts)
            
            print(f"[VectorStore] Retrieved {len(documents)} relevant chunks")
            return context
            
        except Exception as e:
            print(f"[VectorStore ERROR] Query failed: {e}")
            return self._get_default_schema()
    
    def _get_default_schema(self) -> str:
        """Fallback schema if vector search fails"""
        return """
DATABASE SCHEMA:
Tables:
1. resumes (id, filename, name, email, phone, address, linkedin, github, profile, raw_data, created_at)
2. skills (id, resume_id, skill_name, created_at)
3. employment_history (id, resume_id, job_title, company_name, location, start_date, end_date, description, created_at)
4. education (id, resume_id, degree, institution, location, start_date, end_date, created_at)
5. certifications (id, resume_id, certification_name, created_at)
6. languages (id, resume_id, language_name, created_at)

Key Relationships:
- All tables link to resumes via resume_id foreign key
"""
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the vector store"""
        return {
            "total_documents": self.collection.count(),
            "persist_directory": self.persist_directory
        }
    
    def reindex_schema(self):
        """Force reindex of all schema chunks"""
        # Delete existing schema chunks (keep resume contexts)
        try:
            existing = self.collection.get()
            schema_ids = [
                id for id, meta in zip(existing['ids'], existing['metadatas'])
                if meta.get('type') != 'resume_context'
            ]
            if schema_ids:
                self.collection.delete(ids=schema_ids)
        except:
            pass
        
        self._index_schema_chunks()
        print("[VectorStore] Schema reindexed")

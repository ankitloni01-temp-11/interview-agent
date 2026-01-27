import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

class Database:
    def __init__(self, database_path: str = "data/cv_database.db", vector_store=None):
        self.db_path = database_path
        self.vector_store = vector_store
        print(f"[DB] Initializing database at: {self.db_path}")
        self.create_tables()
        vector_status = "with vector store" if vector_store else "standalone"
        print(f"[DB] Database ready ({vector_status})")

    def get_connection(self):
        """Create database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_tables(self):
        """Create unified schema tables"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            print("[DB] Creating tables...")
            
            # Main CVs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resumes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    name TEXT,
                    email TEXT,
                    phone TEXT,
                    address TEXT,
                    linkedin TEXT,
                    github TEXT,
                    profile TEXT,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("[DB] ✓ resumes table created")

            # Skills table (normalized)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id INTEGER NOT NULL,
                    skill_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
                )
            ''')
            print("[DB] ✓ skills table created")

            # Employment history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id INTEGER NOT NULL,
                    job_title TEXT,
                    company_name TEXT,
                    location TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
                )
            ''')
            print("[DB] ✓ employment_history table created")

            # Education table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS education (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id INTEGER NOT NULL,
                    degree TEXT,
                    institution TEXT,
                    location TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
                )
            ''')
            print("[DB] ✓ education table created")

            # Certifications table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS certifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id INTEGER NOT NULL,
                    certification_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
                )
            ''')
            print("[DB] ✓ certifications table created")

            # Languages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS languages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resume_id INTEGER NOT NULL,
                    language_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
                )
            ''')
            print("[DB] ✓ languages table created")

            conn.commit()
            conn.close()
            print("[DB] ✓ All tables created successfully")
            
        except Exception as e:
            print(f"[DB ERROR] Failed to create tables: {e}")
            raise

    def insert_cv(self, filename: str, parsed_data: Dict) -> bool:
        """Insert CV data into normalized database schema"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            contact = parsed_data.get('contact_information', {})
            name = contact.get('name', '')
            email = contact.get('email', '')
            
            # Insert resume record
            cursor.execute('''
                INSERT INTO resumes 
                (filename, name, email, phone, address, linkedin, github, profile, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename,
                name,
                email,
                contact.get('phone', ''),
                contact.get('address', ''),
                contact.get('linkedin', ''),
                contact.get('github', ''),
                parsed_data.get('profile', ''),
                json.dumps(parsed_data)
            ))
            
            resume_id = cursor.lastrowid
            
            # Insert skills
            skills = parsed_data.get('skills', [])
            for skill in skills:
                cursor.execute(
                    'INSERT INTO skills (resume_id, skill_name) VALUES (?, ?)',
                    (resume_id, skill)
                )
            
            # Insert employment history
            employment = parsed_data.get('employment_history', [])
            for job in employment:
                cursor.execute('''
                    INSERT INTO employment_history 
                    (resume_id, job_title, company_name, location, start_date, end_date, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    resume_id,
                    job.get('title', ''),
                    job.get('company', ''),
                    job.get('location', ''),
                    job.get('start_date', ''),
                    job.get('end_date', ''),
                    job.get('description', '')
                ))
            
            # Insert education
            education = parsed_data.get('education', [])
            for edu in education:
                cursor.execute('''
                    INSERT INTO education 
                    (resume_id, degree, institution, location, start_date, end_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    resume_id,
                    edu.get('degree', ''),
                    edu.get('institution', ''),
                    edu.get('location', ''),
                    edu.get('start_date', ''),
                    edu.get('end_date', '')
                ))
            
            # Insert certifications
            certs = parsed_data.get('certifications', [])
            for cert in certs:
                cursor.execute(
                    'INSERT INTO certifications (resume_id, certification_name) VALUES (?, ?)',
                    (resume_id, cert)
                )
            
            # Insert languages
            langs = parsed_data.get('languages', [])
            for lang in langs:
                cursor.execute(
                    'INSERT INTO languages (resume_id, language_name) VALUES (?, ?)',
                    (resume_id, lang)
                )
            
            conn.commit()
            conn.close()
            print(f"[DB] Successfully inserted resume {resume_id}: {name}")
            
            # Sync with vector store if available
            if self.vector_store:
                self.vector_store.add_resume_context(resume_id, parsed_data)
            
            return True
            
        except Exception as e:
            print(f"[DB ERROR] {e}")
            return False

    def get_all_cvs(self) -> List[Dict]:
        """Get all resumes from database with all related data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM resumes ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            cv_dict = dict(row)
            resume_id = row['id']
            
            # Get all related data
            cv_dict['skills'] = self.get_resume_skills(resume_id)
            cv_dict['employment_history'] = self.get_resume_employment(resume_id)
            cv_dict['education'] = self.get_resume_education(resume_id)
            cv_dict['certifications'] = self.get_resume_certifications(resume_id)
            cv_dict['languages'] = self.get_resume_languages(resume_id)
            
            results.append(cv_dict)
        
        return results

    def get_cv_by_id(self, cv_id: int) -> Optional[Dict]:
        """Get specific resume by ID with all related data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM resumes WHERE id = ?', (cv_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        cv_dict = dict(row)
        
        # Get all related data
        cv_dict['skills'] = self.get_resume_skills(cv_id)
        cv_dict['employment_history'] = self.get_resume_employment(cv_id)
        cv_dict['education'] = self.get_resume_education(cv_id)
        cv_dict['certifications'] = self.get_resume_certifications(cv_id)
        cv_dict['languages'] = self.get_resume_languages(cv_id)
        
        return cv_dict

    def get_resume_skills(self, resume_id: int) -> List[str]:
        """Get all skills for a resume"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT skill_name FROM skills WHERE resume_id = ? ORDER BY skill_name', (resume_id,))
        skills = [row[0] for row in cursor.fetchall()]
        conn.close()
        return skills

    def get_resume_employment(self, resume_id: int) -> List[Dict]:
        """Get employment history for a resume"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT job_title, company_name, location, start_date, end_date, description FROM employment_history WHERE resume_id = ? ORDER BY start_date DESC', (resume_id,))
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                'title': row[0],
                'company': row[1],
                'location': row[2],
                'start_date': row[3],
                'end_date': row[4],
                'description': row[5]
            })
        return results

    def get_resume_education(self, resume_id: int) -> List[Dict]:
        """Get education for a resume"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT degree, institution, location, start_date, end_date FROM education WHERE resume_id = ? ORDER BY end_date DESC', (resume_id,))
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                'degree': row[0],
                'institution': row[1],
                'location': row[2],
                'start_date': row[3],
                'end_date': row[4]
            })
        return results

    def get_resume_certifications(self, resume_id: int) -> List[str]:
        """Get certifications for a resume"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT certification_name FROM certifications WHERE resume_id = ?', (resume_id,))
        certs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return certs

    def get_resume_languages(self, resume_id: int) -> List[str]:
        """Get languages for a resume"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT language_name FROM languages WHERE resume_id = ?', (resume_id,))
        langs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return langs

    def export_to_json(self) -> str:
        """Export all resumes to JSON"""
        cvs = self.get_all_cvs()
        output_file = "data/cvs_export.json"
        with open(output_file, 'w') as f:
            json.dump(cvs, f, indent=2, ensure_ascii=False)
        return output_file

    def execute_query(self, query: str) -> List[Dict]:
        """Execute a SQL query and return results"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[DB QUERY ERROR] {e}")
            return []

    def get_schema_info(self) -> str:
        """Get database schema information for chatbot"""
        return """
DATABASE SCHEMA:

1. resumes table:
   - id, filename, name, email, phone, address, linkedin, github, profile, raw_data, created_at

2. skills table:
   - id, resume_id, skill_name, created_at

3. employment_history table:
   - id, resume_id, job_title, company_name, location, start_date, end_date, description

4. education table:
   - id, resume_id, degree, institution, location, start_date, end_date

5. certifications table:
   - id, resume_id, certification_name

6. languages table:
   - id, resume_id, language_name
"""

    def delete_cv(self, cv_id: int) -> bool:
        """Delete a resume"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM resumes WHERE id = ?', (cv_id,))
            conn.commit()
            conn.close()
            
            # Remove from vector store if available
            if self.vector_store:
                self.vector_store.remove_resume_context(cv_id)
            
            return True
        except Exception as e:
            print(f"[DB ERROR] {e}")
            return False

    def get_statistics(self) -> Dict:
        """Get database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM resumes')
        total_resumes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT skill_name) FROM skills')
        total_unique_skills = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_resumes": total_resumes,
            "total_unique_skills": total_unique_skills
        }
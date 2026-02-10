
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from pydantic import BaseModel
import json
import os
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

print("\n" + "="*60)
print("[STARTUP] Initializing CV Parser Application")
print("="*60)



# ============== LIFESPAN ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    print("""
    
    ╔═══════════════════════════════════════════════╗
    ║   🎓 Interview Agent (CV Parsing Base)         ║
    ║         Started Successfully!                  ║
    ╚═══════════════════════════════════════════════╝
    
    🌐 Web App: http://localhost:8000
    📚 Swagger Docs: http://localhost:8000/docs
    
    Features:
    ✅ Upload & Parse CVs
    ✅ Normalized SQLite Schema
    ✅ Query Any Resume Data
    
    """)
    yield
    # Shutdown
    print("\n[SHUTDOWN] Application stopping...")

# ============== INITIALIZE APP ==============

app = FastAPI(
    title="Interview Agent API",
    description="Upload and parse CV/Resume PDF files. Store in normalized SQLite. Base system for Interview Agent.",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create data directory
BASE_DIR = Path(__file__).resolve().parent
os.makedirs(BASE_DIR / "data", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ============== INITIALIZE SERVICES ==============

from src.gemini_parser import GeminiParser
from src.database import Database
from src.vector_store import SchemaVectorStore
from src.agents.orchestrator import Orchestrator

# Global session store
session_store = {}
orchestrator = Orchestrator()

try:
    print("[INIT] Importing config...")
    from src.config import API_KEY
    print(f"[INIT] API_KEY status: {'✓ Found' if API_KEY else '✗ Not found'}")
    
    print("[INIT] Initializing vector store...")
    vector_store = SchemaVectorStore("data/chroma_db")
    print("[✓] Vector store initialized")
    
    print("[INIT] Importing parser...")
    parser = GeminiParser()
    print("[✓] Parser initialized")
    
    print("[INIT] Importing database...")
    db = Database("data/cv_database.db", vector_store=vector_store)
    print("[✓] Database initialized")
    
    print("\n[✓✓✓] All services initialized successfully!")
    print("[✓] RAG enabled with ChromaDB + text-embedding-004")
    print("="*60 + "\n")
    
except Exception as e:
    print(f"\n[✗✗✗] INITIALIZATION ERROR: {e}")
    print("="*60)
    import traceback
    traceback.print_exc()
    parser = None
    db = None


# ============== ROUTES ==============

@app.get("/", response_class=HTMLResponse, tags=["Pages"])
async def home(request: Request):
    """Home page - Upload CV"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/database", response_class=HTMLResponse, tags=["Pages"])
async def database_page(request: Request):
    """Database page - View all CVs"""
    return templates.TemplateResponse("database.html", {"request": request})

@app.get("/cv/{cv_id}", response_class=HTMLResponse, tags=["Pages"])
async def view_cv_page(request: Request, cv_id: int):
    """View individual CV details"""
    if not db:
        return "<p>Database not available</p>"
    cv = db.get_cv_by_id(cv_id)
    if not cv:
        return "<p>CV not found</p>"
    return templates.TemplateResponse("cv_detail.html", {"request": request, "cv_id": cv_id})

@app.get("/ai-assistant/{cv_id}", response_class=HTMLResponse, tags=["Pages"])
async def ai_assistant_page(request: Request, cv_id: int):
    """AI Assistant page for a specific CV"""
    if not db:
        return "<p>Database not available</p>"
    cv = db.get_cv_by_id(cv_id)
    if not cv:
        return "<p>CV not found</p>"
    return templates.TemplateResponse("ai_assistant.html", {"request": request, "cv_id": cv_id, "cv_name": cv['name']})

# ============== API ROUTES ==============

@app.post("/api/parse-cv", tags=["CV Parsing"])
async def parse_cv(file: UploadFile = File(...)):
    """Upload and parse a CV/Resume PDF file."""
    print(f"\n{'='*60}")
    print(f"[📄] Processing: {file.filename}")
    print('='*60)
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        if not parser or not db:
            raise HTTPException(status_code=500, detail="Services not initialized. Check .env file.")
        
        content = await file.read()
        print(f"[📊] File size: {len(content)} bytes")
        
        parsed_data = parser.parse_cv(content)
        
        if "error" in parsed_data:
            raise HTTPException(status_code=400, detail=parsed_data["error"])
        
        print(f"[✓] Successfully parsed CV")
        print(f"[👤] Name: {parsed_data.get('contact_information', {}).get('name')}")
        
        success = db.insert_cv(file.filename, parsed_data)
        if success:
            print(f"[✓] Stored in normalized database")
        else:
            print(f"[⚠] Database storage failed")
        
        print('='*60 + "\n")
        return parsed_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[✗] Error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/api/cvs", tags=["Database"])
async def get_all_cvs():
    """Get all CVs from database."""
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")
    
    return db.get_all_cvs()

@app.get("/api/cvs/{cv_id}", tags=["Database"])
async def get_cv_detail(cv_id: int):
    """Get specific CV by ID."""
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")
    
    cv = db.get_cv_by_id(cv_id)
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    
    return cv

@app.delete("/api/cvs/{cv_id}", tags=["Database"])
async def delete_cv(cv_id: int):
    """Delete a CV from database."""
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")
    
    cv = db.get_cv_by_id(cv_id)
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    

    
    db.delete_cv(cv_id)
    return {"message": f"CV '{cv['name']}' deleted successfully"}

@app.get("/api/stats", tags=["Database"])
async def get_statistics():
    """Get database statistics."""
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")
    
    return db.get_statistics()

@app.get("/api/export", tags=["Database"])
async def export_cvs():
    """Export all CVs to JSON file."""
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")
    
    output_file = db.export_to_json()
    return FileResponse(
        output_file,
        media_type="application/json",
        filename="cvs_export.json"
    )



@app.get("/api/health", tags=["System"])
async def health_check():
    """System health check endpoint"""
    return {"status": "healthy", "chatbot": "Disabled"}

# ============== CHAT AGENT INTEGRATION ==============
from src.agents.orchestrator import Orchestrator

class ChatMessage(BaseModel):
    message: str

orchestrator = Orchestrator()

@app.post("/api/chat/{cv_id}", tags=["AI Assistant"])
async def chat_with_agent(cv_id: int, message: ChatMessage):
    """
    Chat with the Interview Assistant for a specific CV using Orchestrator.
    """
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")
    
    cv_data = db.get_cv_by_id(cv_id)
    if not cv_data:
        raise HTTPException(status_code=404, detail="CV not found")

    user_message = message.message
    
    # Simple session management
    if cv_id not in session_store:
        contact = cv_data.get('contact_information', {})
        session_store[cv_id] = {
            "cv_id": cv_id,
            "cv_data": cv_data,
            "history": [],
            "state": "START",
            "unverified_asked": 0,
            "projects_asked": 0,
            "covered_topics": [],
            "current_topic": None,
            "unverified_skills": [],
            "discovered_projects": [],
            "github_verified": contact.get('github_verified', False),
            "linkedin_verified": contact.get('linkedin_verified', False),
            "job_description": "Technical Role"
        }
    
    context = session_store[cv_id]
    
    try:
        # Route the message through the orchestrator
        result = await orchestrator.route(user_message, context)
        
        # Update session store with new context
        session_store[cv_id] = result.get('context', context)
        
        # Append to history
        session_store[cv_id]['history'].append({"role": "user", "content": user_message})
        session_store[cv_id]['history'].append({
            "role": "assistant", 
            "content": result['response'], 
            "agent": result.get('agent', 'Assistant')
        })
            
        return {
            "response": result['response'],
            "agent": result.get('agent', 'Assistant'),
            "context": {
                "state": context.get('state', 'INTERVIEWING'),
                "unverified_asked": context.get('unverified_asked', 0),
                "projects_asked": context.get('projects_asked', 0)
            }
        }
        
    except Exception as e:
        print(f"[Chat Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{cv_id}", tags=["AI Assistant"])
async def get_chat_history(cv_id: int):
    """Get chat history for a session"""
    if cv_id in session_store:
        return {"history": session_store[cv_id].get('history', [])}
    return {"history": []}
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    print(f"[✗] Unhandled exception: {exc}")
    return HTMLResponse(
        content=f"<h1>Error 500</h1><p>{str(exc)}</p>",
        status_code=500
    )

# ============== RUN ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

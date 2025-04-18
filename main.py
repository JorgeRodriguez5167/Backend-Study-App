from pydantic import BaseModel
from summurization import summarize_and_categorize
from fastapi import FastAPI, HTTPException, Request, Body
from pydantic import BaseModel
from sqlmodel import Session, select
from models import User, Note
from databases import engine, create_db_and_tables
from fastapi import FastAPI, UploadFile, File
from model import SpeechToTextModel
import shutil
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import JSONResponse
import uvicorn
from typing import Optional, List
from datetime import datetime

# Create the FastAPI app
app = FastAPI(title="Study Assistant API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize models
stt_model = SpeechToTextModel()

# Create database tables on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# ----------------------
# Request/Response Models
# ----------------------

class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    first_name: str
    last_name: str
    age: int
    major: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    age: int
    major: str

class NoteCreate(BaseModel):
    user_id: int
    audio: str
    transcription: Optional[str] = None
    summarized_notes: Optional[str] = None
    category: Optional[str] = None

class NoteResponse(BaseModel):
    id: int
    user_id: int
    audio: str
    transcription: str
    summarized_notes: str
    category: str
    created_at: datetime

class TextRequest(BaseModel):
    text: str

class SummaryResponse(BaseModel):
    summary: str
    category: str

# ----------------------
# User Endpoints
# ----------------------

@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    """Create a new user"""
    with Session(engine) as session:
        # Check if username already exists
        existing = session.exec(select(User).where(User.username == user.username)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Create new user
        db_user = User(
            username=user.username,
            password=user.password,  # In production, hash this password
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            age=user.age,
            major=user.major
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        
        return db_user

@app.get("/users", response_model=List[UserResponse])
def get_users():
    """Get all users"""
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        return users

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    """Get a specific user by ID"""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

# ----------------------
# Notes Endpoints
# ----------------------

@app.post("/notes", response_model=NoteResponse)
def create_note(note: NoteCreate):
    """Create a new note"""
    with Session(engine) as session:
        # Verify user exists
        user = session.get(User, note.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create new note
        db_note = Note(
            user_id=note.user_id,
            audio=note.audio,
            transcription=note.transcription or "",
            summarized_notes=note.summarized_notes or "",
            category=note.category or ""
        )
        session.add(db_note)
        session.commit()
        session.refresh(db_note)
        
        return db_note

@app.get("/notes", response_model=List[NoteResponse])
def get_notes():
    """Get all notes"""
    with Session(engine) as session:
        notes = session.exec(select(Note)).all()
        return notes

@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int):
    """Get a specific note by ID"""
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return note

@app.get("/users/{user_id}/notes", response_model=List[NoteResponse])
def get_user_notes(user_id: int):
    """Get all notes for a specific user"""
    with Session(engine) as session:
        # Verify user exists
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's notes
        notes = session.exec(select(Note).where(Note.user_id == user_id)).all()
        return notes

# ----------------------
# Transcription Endpoint
# ----------------------

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio file"""
    # Save uploaded file temporarily
    temp_path = Path("temp_audio.wav")
    
    with temp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Transcribe audio
    try:
        transcript = stt_model.transcribe(str(temp_path))
        temp_path.unlink()  # Clean up
        return {"transcription": transcript}
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")

# ----------------------
# Summarization Endpoint
# ----------------------

@app.post("/summarize", response_model=SummaryResponse)
def summarize_text(req: TextRequest):
    """Summarize and categorize text"""
    if not req.text or len(req.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    summary, category = summarize_and_categorize(req.text)
    return {"summary": summary, "category": category}

# ----------------------
# Root Endpoint
# ----------------------

@app.get("/")
def read_root():
    """API root endpoint"""
    return {
        "name": "Study Assistant API",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/users", "methods": ["GET", "POST"]},
            {"path": "/users/{user_id}", "methods": ["GET"]},
            {"path": "/users/{user_id}/notes", "methods": ["GET"]},
            {"path": "/notes", "methods": ["GET", "POST"]},
            {"path": "/notes/{note_id}", "methods": ["GET"]},
            {"path": "/transcribe", "methods": ["POST"]},
            {"path": "/summarize", "methods": ["POST"]}
        ]
    }

# ----------------------
# Run the Application
# ----------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False) 




from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel
from summurization import summarize_and_categorize
from fastapi import FastAPI, HTTPException, Request, Body
from pydantic import BaseModel
from sqlmodel import Session, select
from models import User, Note
from databases import engine, create_db_and_tables
from fastapi import FastAPI, UploadFile, File
import shutil
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import JSONResponse
import uvicorn
from typing import Optional, List
from datetime import datetime, date
import tempfile
import logging
from logging.handlers import RotatingFileHandler
from stt_model import SpeechToTextModel
from fastapi.responses import StreamingResponse
from pathlib import Path
from pydub import AudioSegment
from fastapi import Query
from passlib.context import CryptContext

# Set up logging
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Configure root logger
logging.basicConfig(
    level=getattr(logging, log_level),
    format=log_format,
    handlers=[
        # Console handler
        logging.StreamHandler(),
        # File handler with rotation
        RotatingFileHandler(
            os.environ.get("LOG_FILE", "app.log"),
            maxBytes=10485760,  # 10MB
            backupCount=3
        )
    ]
)

# Get logger for this module
logger = logging.getLogger(__name__)
logger.info(f"Starting application with log level: {log_level}")

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

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create database tables on startup
@app.on_event("startup")
def on_startup():
    logger.info("Application startup: Creating database tables")
    try:
        create_db_and_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

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
    date_of_birth: Optional[date] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    age: int
    major: str
    date_of_birth: Optional[date] = None

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

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str

# ----------------------
# User Endpoints
# ----------------------

@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    """Create a new user"""
    try:
        # Log the incoming request data (excluding password)
        safe_user_data = {**user.dict()}
        safe_user_data["password"] = "***REDACTED***"
        logger.info(f"User registration request received: {safe_user_data}")
        
        with Session(engine) as session:
            # Check if username already exists
            existing_username = session.exec(select(User).where(User.username == user.username)).first()
            if existing_username:
                logger.warning(f"Registration failed: Username '{user.username}' already exists")
                raise HTTPException(status_code=400, detail="Username already exists")
            
            # Check if email already exists
            existing_email = session.exec(select(User).where(User.email == user.email)).first()
            if existing_email:
                logger.warning(f"Registration failed: Email '{user.email}' already registered")
                raise HTTPException(status_code=400, detail="Email already registered")
            
            try:
                # Hash the password
                logger.debug("Attempting to hash password")
                hashed_password = pwd_context.hash(user.password)
                logger.debug("Password hashed successfully")
                
                # Create new user
                db_user = User(
                    username=user.username,
                    password=hashed_password,  # Store hashed password
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    age=user.age,
                    major=user.major,
                    date_of_birth=user.date_of_birth
                )
                
                logger.debug("Adding user to session")
                session.add(db_user)
                logger.debug("Committing session")
                session.commit()
                logger.debug("Session committed successfully")
                session.refresh(db_user)
                logger.info(f"User created successfully: {user.username}")
                return db_user
            except Exception as e:
                logger.error(f"Error creating user in database: {str(e)}", exc_info=True)
                session.rollback()
                raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log any unexpected errors
        error_msg = f"Unexpected error in create_user: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/register-simple", response_model=UserResponse)
def create_user_simple(user: UserCreate):
    """Create a new user without password hashing - for testing only"""
    try:
        # Log the incoming request data (excluding password)
        safe_user_data = {**user.dict()}
        safe_user_data["password"] = "***REDACTED***"
        logger.info(f"Simple user registration request received: {safe_user_data}")
        
        with Session(engine) as session:
            # Check if username already exists
            existing_username = session.exec(select(User).where(User.username == user.username)).first()
            if existing_username:
                logger.warning(f"Simple registration failed: Username '{user.username}' already exists")
                raise HTTPException(status_code=400, detail="Username already exists")
            
            # Check if email already exists
            existing_email = session.exec(select(User).where(User.email == user.email)).first()
            if existing_email:
                logger.warning(f"Simple registration failed: Email '{user.email}' already registered")
                raise HTTPException(status_code=400, detail="Email already registered")
            
            try:
                # Create new user with plain text password (not secure, for testing only)
                db_user = User(
                    username=user.username,
                    password=user.password,  # Plain text for testing
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    age=user.age,
                    major=user.major,
                    date_of_birth=user.date_of_birth
                )
                
                logger.debug("Adding user to session (simple)")
                session.add(db_user)
                logger.debug("Committing session (simple)")
                session.commit()
                logger.debug("Session committed successfully (simple)")
                session.refresh(db_user)
                
                logger.info(f"User created successfully with simple method: {user.username}")
                return db_user
            except Exception as e:
                error_msg = f"Database error: {str(e)}"
                logger.error(f"Error creating user in database (simple): {error_msg}", exc_info=True)
                session.rollback()
                raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error in create_user_simple: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

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

@app.post("/login", response_model=TokenResponse)
def login(user_credentials: UserLogin):
    """Authenticate a user and return a token"""
    with Session(engine) as session:
        # Find user by username
        user = session.exec(select(User).where(User.username == user_credentials.username)).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Verify password
        if not pwd_context.verify(user_credentials.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Create a simple token (in a real app, you'd use JWT)
        # For now, we're just returning user details
        return {
            "access_token": f"user_{user.id}_{user.username}",  # This is a placeholder, not secure
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username
        }

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
async def transcribe_audio(
    file: UploadFile = File(...),
    stream: bool = Query(False)
):
    print(f"[DEBUG] Received file: {file.filename}, type: {file.content_type}, stream={stream}")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    try:
        suffix = Path(file.filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_path = Path(tmp.name)

        # Convert to .wav and resample to 16kHz mono if needed
        if suffix == ".wav":
            try:
                import wave
                with wave.open(temp_path, 'rb') as wf:
                    sr = wf.getframerate()
                    ch = wf.getnchannels()
                if sr != 16000 or ch != 1:
                    audio = AudioSegment.from_file(temp_path)
                    audio = audio.set_frame_rate(16000).set_channels(1)
                    print(f"[DEBUG] Resampling audio to 16kHz mono for Whisper processing")
                    audio.export(temp_path, format="wav")
            except Exception as e:
                audio = AudioSegment.from_file(temp_path)
                if audio.frame_rate != 16000 or audio.channels != 1:
                    audio = audio.set_frame_rate(16000).set_channels(1)
                    print(f"[DEBUG] Resampling audio to 16kHz mono for Whisper processing")
                audio.export(temp_path, format="wav")
        else:
            audio = AudioSegment.from_file(temp_path)
            if audio.frame_rate != 16000 or audio.channels != 1:
                audio = audio.set_frame_rate(16000).set_channels(1)
                print(f"[DEBUG] Resampling audio to 16kHz mono for Whisper processing")
            wav_path = temp_path.with_suffix(".wav")
            audio.export(wav_path, format="wav")
            temp_path.unlink()
            temp_path = wav_path

        if stream:
            def generate():
                for chunk in stt_model.transcribe_stream(str(temp_path)):
                    yield chunk
                temp_path.unlink()

            return StreamingResponse(generate(), media_type="text/plain")

        else:
            transcript = stt_model.transcribe(str(temp_path))
            temp_path.unlink()
            return JSONResponse({"transcription": transcript})

    except Exception as e:
        print(f"[ERROR] Transcription error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

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

@app.get("/ping")
def ping():
    return {"ping": "pong"}

@app.get("/health")
def health():
    """Health check endpoint for API and Database"""
    health_status = {"api": "ok"}
    
    # Check database connection
    try:
        with Session(engine) as session:
            # Simple query to test database connection
            session.exec(select(User).limit(1)).all()
            health_status["database"] = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["database"] = "error"
        health_status["database_error"] = str(e)
    
    return health_status


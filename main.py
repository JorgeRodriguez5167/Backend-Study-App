#Rodolfo and Jorge's FastAPI set up
from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel
from summurization import summarize_and_categorize, summarize_text
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
from guide import generate_study_guide

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
    major: str
    date_of_birth: date
    age: Optional[int] = None  # Age will be calculated from date_of_birth

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
    title: Optional[str] = None
    transcription: Optional[str] = None
    summarized_notes: Optional[str] = None
    category: Optional[str] = None

class NoteResponse(BaseModel):
    id: int
    user_id: int
    title: str
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

class StudyGuideRequest(BaseModel):
    category: str
    user_id: int

class StudyGuideResponse(BaseModel):
    guide: str
    category: str

class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

class PasswordUpdateRequest(BaseModel):
    current_password: str
    new_password: str

# ----------------------
# User Endpoints
# ----------------------

@app.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Create a new user with password hashing"""
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
            
            # Hash the password
            try:
                logger.debug(f"Hashing password for user: {user.username}")
                hashed_password = pwd_context.hash(user.password)
                logger.debug("Password hashed successfully")
            except Exception as e:
                logger.error(f"Password hashing error: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail="Error processing password")
            
            try:
                # Calculate age from date of birth
                today = date.today()
                calculated_age = today.year - user.date_of_birth.year - ((today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day))
                
                # Create new user with hashed password
                db_user = User(
                    username=user.username,
                    password=hashed_password,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    age=calculated_age,  # Use calculated age
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
                error_msg = f"Database error: {str(e)}"
                logger.error(f"Error creating user in database: {error_msg}", exc_info=True)
                session.rollback()
                raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
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
                # Calculate age from date of birth
                today = date.today()
                calculated_age = today.year - user.date_of_birth.year - ((today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day))
                
                # Create new user with plain text password (not secure, for testing only)
                db_user = User(
                    username=user.username,
                    password=user.password,  
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    age=calculated_age,  # Use calculated age
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

#API user registration and log in worked on by Jorge
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
        
        # For now, we're just returning user details
        return {
            "access_token": f"user_{user.id}_{user.username}",  # This is a placeholder, not secure
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username
        }

@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdateRequest):
    """Update a user's profile information"""
    try:
        with Session(engine) as session:
            # Get the user
            db_user = session.get(User, user_id)
            if not db_user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Check if email is being updated and if it's already taken
            if user_update.email and user_update.email != db_user.email:
                existing_email = session.exec(select(User).where(User.email == user_update.email)).first()
                if existing_email:
                    raise HTTPException(status_code=400, detail="Email already registered")
            
            # Update fields if provided
            if user_update.first_name is not None:
                db_user.first_name = user_update.first_name
            if user_update.last_name is not None:
                db_user.last_name = user_update.last_name
            if user_update.email is not None:
                db_user.email = user_update.email
            
            # Save changes
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
            
            return db_user
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error in update_user: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.put("/users/{user_id}/password", response_model=dict)
def update_password(user_id: int, password_update: PasswordUpdateRequest):
    """Update a user's password"""
    try:
        with Session(engine) as session:
            # Get the user
            db_user = session.get(User, user_id)
            if not db_user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Verify current password
            if not pwd_context.verify(password_update.current_password, db_user.password):
                raise HTTPException(status_code=401, detail="Current password is incorrect")
            
            # Hash and update new password
            db_user.password = pwd_context.hash(password_update.new_password)
            
            # Save changes
            session.add(db_user)
            session.commit()
            
            return {"message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error in update_password: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

# ----------------------
# Notes Endpoints
# ----------------------
#Note and Study guide API and logic by Jorge
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
            title=note.title or "Untitled Note",
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
    # Debug: Confirm file received
    print(f"[DEBUG] Received file: {file.filename}, type: {file.content_type}, stream={stream}")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Debug: Check file size before processing
    try:
        contents = await file.read()
        print(f"[DEBUG] File content size: {len(contents)} bytes")
        await file.seek(0)  # Reset pointer so we can read it again
    except Exception as e:
        print(f"[ERROR] Could not read uploaded file: {e}")
        raise HTTPException(status_code=400, detail="File read error")

    try:
        suffix = Path(file.filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_path = Path(tmp.name)

        # Convert to .wav if needed
        if suffix != ".wav":
            wav_path = temp_path.with_suffix(".wav")
            audio = AudioSegment.from_file(temp_path)
            audio.export(wav_path, format="wav")
            temp_path.unlink()
            temp_path = wav_path

        if stream:
            def generate():
                for chunk in stt_model.transcribe_stream(str(temp_path)):
                    yield chunk
                temp_path.unlink()
            return StreamingResponse(generate(), media_type="text/plain")

        transcript = stt_model.transcribe(str(temp_path))
        temp_path.unlink()
        return JSONResponse({"transcription": transcript})

    except Exception as e:
        print(f"[ERROR] Transcription error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ----------------------
# Summarization Endpoint
# ----------------------
#Summurization API and logic worked on by Jorge 
@app.post("/summarize", response_model=SummaryResponse)
def summarize_text_endpoint(req: TextRequest):
    """Summarize and categorize text"""
    if not req.text or len(req.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    summary, category = summarize_and_categorize(req.text)
    return {"summary": summary, "category": category}

# ----------------------
# Study Guide Endpoint
# ----------------------

@app.post("/study-guide", response_model=StudyGuideResponse)
def create_study_guide(req: StudyGuideRequest):
    """Generate a study guide based on notes with a specific category for a specific user"""
    try:
        if not req.category or len(req.category.strip()) == 0:
            raise HTTPException(status_code=400, detail="Category cannot be empty")
        
        if not req.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # Verify user exists
        with Session(engine) as session:
            user = session.get(User, req.user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"Generating study guide for user {req.user_id}, category: {req.category}")
        study_guide = generate_study_guide(req.category, req.user_id)
        logger.info(f"Study guide generation completed for user {req.user_id}, category: {req.category}")
        
        return {"guide": study_guide, "category": req.category}
    except Exception as e:
        error_msg = f"Error generating study guide: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

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
            {"path": "/summarize", "methods": ["POST"]},
            {"path": "/study-guide", "methods": ["POST"]}
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


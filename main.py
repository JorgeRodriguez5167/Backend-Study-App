from pydantic import BaseModel
from summurization import summarize_and_categorize
from fastapi import FastAPI, HTTPException, APIRouter, UploadFile, File
from sqlmodel import Session, select
from models import User, Note
from databases import engine, create_db_and_tables
from model import SpeechToTextModel
import shutil
from pathlib import Path
import os
import tempfile

# Create API router for all routes
router = APIRouter()

# Create the FastAPI app with docs URL configuration
app = FastAPI(
    docs_url="/",  # Serve Swagger UI at /
    redoc_url="/redoc"  # Serve ReDoc at /redoc
)

# Read model ID from environment variable for deployment
model_id = os.getenv("MODEL_ID", "facebook/wav2vec2-large-960h-lv60-self")
stt_model = SpeechToTextModel(model_id=model_id)

@router.on_event("startup")
def on_startup():
    create_db_and_tables()

# ------------------------
# USERS
# ------------------------

@router.post("/users/", response_model=User)
def create_user(user: User):
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == user.username)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

@router.get("/users/", response_model=list[User])
def get_users():
    with Session(engine) as session:
        return session.exec(select(User)).all()

# ------------------------
# NOTES
# ------------------------

@router.post("/notes/", response_model=Note)
def create_note(note: Note):
    with Session(engine) as session:
        user = session.get(User, note.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session.add(note)
        session.commit()
        session.refresh(note)
        return note

@router.get("/notes/", response_model=list[Note])
def get_notes():
    with Session(engine) as session:
        return session.exec(select(Note)).all()

# ------------------------
# SUMMARIZATION
# ------------------------

class TextRequest(BaseModel):
    text: str

class SummaryResponse(BaseModel):
    summary: str
    category: str

@router.post("/summarize/", response_model=SummaryResponse)
def summarize_text(req: TextRequest):
    summary, category = summarize_and_categorize(req.text)
    return {"summary": summary, "category": category}

# ------------------------
# TRANSCRIPTION
# ------------------------

@router.post("/transcribe/")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            shutil.copyfileobj(file.file, temp_audio)
            temp_audio_path = temp_audio.name

        transcript = stt_model.transcribe(temp_audio_path)
        os.remove(temp_audio_path)
        return {"transcription": transcript}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

# Mount routes
app.include_router(router, prefix="/docs")




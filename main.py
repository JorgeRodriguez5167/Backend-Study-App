from fastapi import FastAPI, HTTPException, APIRouter, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware  # Enable CORS
from pydantic import BaseModel
from summurization import summarize_and_categorize
from sqlmodel import Session, select
from models import User, Note
from databases import engine, create_db_and_tables
from model import SpeechToTextModel
import shutil
import tempfile
import os

# Create API router for all routes
router = APIRouter()

# Initialize FastAPI app with custom docs URLs
app = FastAPI(
    docs_url="/",    # Serve Swagger UI at root ("/")
    redoc_url="/redoc"
)

# Enable CORS for all origins (allow frontend to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize speech-to-text model (Wav2Vec2) with optional env override
model_id = os.getenv("MODEL_ID", "facebook/wav2vec2-large-960h-lv60-self")
stt_model = SpeechToTextModel(model_id)  # use model from local implementation

@app.on_event("startup")
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
    """Upload an audio file and return its transcription."""
    try:
        # Save the uploaded file to a temporary WAV file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            shutil.copyfileobj(file.file, temp_audio)
            temp_audio_path = temp_audio.name
        # Transcribe audio using the STT model
        transcript = stt_model.transcribe(temp_audio_path)
        # Clean up temporary file
        os.remove(temp_audio_path)
        return {"transcription": transcript or "(No transcription found)"}
    except Exception as e:
        # Handle any errors during transcription
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

# Include all routes with a prefix (so API endpoints are under /docs)
app.include_router(router, prefix="/docs")



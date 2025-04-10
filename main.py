from pydantic import BaseModel
from summurization import summarize_and_categorize
from fastapi import FastAPI, HTTPException
from sqlmodel import Session, select
from models import User, Note
from databases import engine, create_db_and_tables
from fastapi import FastAPI, UploadFile, File
from model import SpeechToTextModel
import shutil
from pathlib import Path

app = FastAPI()
stt_model = SpeechToTextModel()



@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# ------------------------
# USERS
# ------------------------

@app.post("/users/", response_model=User)
def create_user(user: User):
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == user.username)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

@app.get("/users/", response_model=list[User])
def get_users():
    with Session(engine) as session:
        return session.exec(select(User)).all()

# ------------------------
# NOTES
# ------------------------

@app.post("/notes/", response_model=Note)
def create_note(note: Note):
    with Session(engine) as session:
        user = session.get(User, note.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session.add(note)
        session.commit()
        session.refresh(note)
        return note

@app.get("/notes/", response_model=list[Note])
def get_notes():
    with Session(engine) as session:
        return session.exec(select(Note)).all()
    
class TextRequest(BaseModel):
    text: str

class SummaryResponse(BaseModel):
    summary: str
    category: str

@app.post("/summarize/", response_model=SummaryResponse)
def summarize_text(req: TextRequest):
    summary, category = summarize_and_categorize(req.text)
    return {"summary": summary, "category": category}

@app.post("/transcribe/")
async def transcribe_audio(file: UploadFile = File(...)):
    temp_path = Path("temp_audio.wav")

    with temp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    transcript = stt_model.transcribe(str(temp_path))
    temp_path.unlink()  # Clean up

    return {"transcription": transcript}
# PATCH: Fix Railway deployment compatibility (no streaming)
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import tempfile
import shutil
from model import SpeechToTextModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stt_model = SpeechToTextModel("base")

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    stream: bool = Query(False)
):
    print(f"[DEBUG] Received file: {file.filename}, type: {file.content_type}, stream={stream}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = Path(tmp.name)

    transcript = stt_model.transcribe(str(temp_path))
    temp_path.unlink()
    return JSONResponse({"transcription": transcript})


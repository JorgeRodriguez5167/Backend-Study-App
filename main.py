from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import tempfile
import shutil
import logging
from model import SpeechToTextModel

logging.basicConfig(level=logging.INFO)

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
    logging.info(f"[DEBUG] Received file: {file.filename}, type: {file.content_type}, stream={stream}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = Path(tmp.name)

    try:
        transcript = stt_model.transcribe(str(temp_path))
        logging.info(f"[DEBUG] Transcript: {transcript[:80]}...")
    except Exception as e:
        logging.error(f"[ERROR] Transcription failed: {e}")
        raise HTTPException(status_code=500, detail="Transcription failed")
    finally:
        temp_path.unlink()

    return JSONResponse({"transcription": transcript})



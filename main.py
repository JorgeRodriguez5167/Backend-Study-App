from fastapi import FastAPI, APIRouter, UploadFile, File, Query, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil, tempfile
from pathlib import Path
from model import SpeechToTextModel

app = FastAPI(
    title="Study Assistant API",
    description="Transcribes and summarizes audio notes",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()
stt_model = SpeechToTextModel("base")

@router.post("/transcribe")
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

app.include_router(router)



# model.py

from faster_whisper import WhisperModel
import os

class SpeechToTextModel:
    def __init__(self, model_size_or_path="base"):
        print(f"[INFO] Loading Whisper model: {model_size_or_path}")
        self.model = WhisperModel(model_size_or_path, compute_type="int8", device="cpu")

    def transcribe(self, file_path: str) -> str:
        print(f"[DEBUG] Starting full transcription for: {file_path}")
        segments, _ = self.model.transcribe(file_path)
        full_text = ""
        for segment in segments:
            print(f"[CHUNK] {segment.start:.2f}s - {segment.end:.2f}s: {segment.text.strip()}")
            full_text += segment.text.strip() + " "
        print(f"[INFO] Transcription complete. Length: {len(full_text)} characters.")
        return full_text.strip()

    def transcribe_stream(self, file_path: str):
        print(f"[DEBUG] Starting stream transcription for: {file_path}")
        try:
            segments, _ = self.model.transcribe(file_path)
            for segment in segments:
                chunk = segment.text.strip()
                print(f"[CHUNK] {segment.start:.2f}s - {segment.end:.2f}s: {chunk}")
                yield chunk + "\n"
        except Exception as e:
            print(f"[ERROR] Stream transcription failed: {e}")
            yield "[ERROR] Failed to transcribe\n"

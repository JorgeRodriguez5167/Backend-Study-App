from faster_whisper import WhisperModel

class SpeechToTextModel:
    def __init__(self, model_size_or_path="base"):
        print(f"[INFO] Loading Whisper model: {model_size_or_path}")
        self.model = WhisperModel(model_size_or_path, device="cpu", compute_type="int8")

    def transcribe(self, file_path: str) -> str:
        print(f"[DEBUG] Transcribing file: {file_path}")
        segments, _ = self.model.transcribe(file_path)
        full_text = " ".join([segment.text for segment in segments])
        print(f"[DEBUG] Transcription complete. Length: {len(full_text)} characters")
        return full_text

    def transcribe_stream(self, file_path: str):
        print(f"[DEBUG] Streaming transcription for file: {file_path}")
        segments, _ = self.model.transcribe(file_path)
        for segment in segments:
            yield segment.text + " "

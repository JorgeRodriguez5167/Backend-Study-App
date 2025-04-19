from faster_whisper import WhisperModel

class SpeechToTextModel:
    def __init__(self, model_size_or_path="base"):
        self.model = WhisperModel(model_size_or_path, device="cpu", compute_type="int8")

    def transcribe(self, file_path: str) -> str:
        segments, _ = self.model.transcribe(file_path)
        return " ".join([segment.text for segment in segments])

    def transcribe_stream(self, file_path: str):
        segments, _ = self.model.transcribe(file_path)
        for segment in segments:
            yield segment.text + " "
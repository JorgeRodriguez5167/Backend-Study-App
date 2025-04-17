import torch
import torchaudio
import os
import io
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from pydub import AudioSegment
import numpy as np
import tempfile

class SpeechToTextModel:
    def __init__(self, model_id=None):
        model_id = model_id or os.getenv("MODEL_ID", "facebook/wav2vec2-large-960h")
        print(f"[INFO] Loading model and processor: {model_id}")
        self.processor = Wav2Vec2Processor.from_pretrained(model_id)
        self.model = Wav2Vec2ForCTC.from_pretrained(model_id)
        self.model.eval()
        print("Model ready.")

    def preprocess_audio(self, file_path):
        print(f"[DEBUG] Preprocessing: {file_path}")

        file_ext = Path(file_path).suffix.lower()
        if file_ext not in [".wav", ".mp3", ".m4a", ".aac"]:
            raise ValueError("Unsupported audio format")

        if file_ext != ".wav":
            audio = AudioSegment.from_file(file_path)
            file_path = tempfile.mktemp(suffix=".wav")
            audio.export(file_path, format="wav")

        waveform, sample_rate = torchaudio.load(file_path)
        if sample_rate != 16000:
            waveform = torchaudio.functional.resample(waveform, sample_rate, 16000)

        waveform = waveform.mean(dim=0)  # convert to mono
        print(f"[DEBUG] Audio loaded. Shape: {waveform.shape}, Sample Rate: 16000")
        return waveform.numpy(), 16000

    def chunk_audio(self, waveform, sample_rate, chunk_length=30):
        total_len = waveform.shape[0]
        chunk_size = chunk_length * sample_rate
        print(f"[DEBUG] Duration: {total_len / sample_rate:.2f} seconds")
        print(f"[DEBUG] Min/Max: {waveform.min():.4f} / {waveform.max():.4f}")

        chunks = []
        for start in range(0, total_len, chunk_size):
            end = min(start + chunk_size, total_len)
            chunks.append(waveform[start:end])
        print(f"[DEBUG] Chunking complete. {len(chunks)} chunks.")
        return chunks

    def transcribe_chunk(self, chunk, sample_rate):
        inputs = self.processor(chunk, sampling_rate=sample_rate, return_tensors="pt", padding=True)
        with torch.no_grad():
            logits = self.model(**inputs).logits
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.processor.batch_decode(predicted_ids)[0]
        return transcription.lower().strip()

    def transcribe(self, file_path):
        waveform, sample_rate = self.preprocess_audio(file_path)
        chunks = self.chunk_audio(waveform, sample_rate)
        transcript = []

        for chunk in chunks:
            text = self.transcribe_chunk(chunk, sample_rate)
            print(f"[DEBUG] Chunk transcription: {text[:80]}...")
            transcript.append(text)

        final_transcript = " ".join(transcript)
        print(f"[DEBUG] Final transcription: {final_transcript[:100]}...")
        return final_transcript



from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import os
import torch
import numpy as np
from pydub import AudioSegment  # Added for broader audio format support
from concurrent.futures import ThreadPoolExecutor

class SpeechToTextModel:
    def __init__(self, model_name="facebook/wav2vec2-large-960h-lv60-self"):
        print("[INFO] Loading model and processor...")
        self.processor = Wav2Vec2Processor.from_pretrained(model_name)
        self.model = Wav2Vec2ForCTC.from_pretrained(model_name)
        self.model.eval()
        self.sample_rate = 16000
        self.chunk_duration = 30  # seconds

    def transcribe(self, audio_path):
        print(f"[DEBUG] Preprocessing: {audio_path}")
        try:
            # Load and convert to mono, 16kHz, float32 using pydub
            sound = AudioSegment.from_file(audio_path)
            sound = sound.set_frame_rate(self.sample_rate).set_channels(1)
            samples = np.array(sound.get_array_of_samples()).astype(np.float32) / (2**15)
            audio = samples
            sr = self.sample_rate

            print(f"[DEBUG] Audio loaded. Shape: {audio.shape}, Sample Rate: {sr}")
            print(f"[DEBUG] Duration: {round(len(audio) / sr, 2)} seconds")
            print(f"[DEBUG] Min/Max: {audio.min():.4f} / {audio.max():.4f}")

            if len(audio) == 0 or audio.max() - audio.min() < 1e-5:
                print("[WARNING] Audio is silent or invalid.")
                return "(audio unreadable)"

            chunks = self.chunk_audio(audio)
            print(f"[DEBUG] Chunking complete. {len(chunks)} chunks.")

            # Transcribe each chunk in parallel
            with ThreadPoolExecutor() as executor:
                results = list(executor.map(self.transcribe_chunk, chunks))

            full_transcription = " ".join(results)
            print(f"[DEBUG] Final transcription: {full_transcription[:100]}...")
            return full_transcription.strip()
        except Exception as e:
            print(f"[ERROR] Transcription failed: {str(e)}")
            return None

    def chunk_audio(self, audio):
        max_samples = int(self.chunk_duration * self.sample_rate)
        overlap = int(0.1 * self.sample_rate)  # 100ms overlap
        chunks = []
        i = 0
        while i < len(audio):
            end = min(i + max_samples, len(audio))
            chunk = audio[i:end]
            chunks.append(chunk)
            i += max_samples - overlap
        return chunks

    def transcribe_chunk(self, chunk):
        try:
            input_values = self.processor(chunk, sampling_rate=self.sample_rate, return_tensors="pt").input_values
            logits = self.model(input_values).logits
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = self.processor.batch_decode(predicted_ids)[0]
            print(f"[DEBUG] Chunk transcription: {transcription.strip()[:80]}...")
            return transcription.lower().strip()
        except Exception as e:
            print(f"[ERROR] Chunk failed: {str(e)}")
            return ""



from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import os
import torch
import numpy as np
import librosa
import shutil
import noisereduce as nr
import tempfile
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm


class SpeechToTextModel:
    def __init__(self):
        print("Loading model (facebook/wav2vec2-large-960h)...")
        self.processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-large-960h")
        self.model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-large-960h")
        self.model.eval()
        print("Model ready.")

    def preprocess_audio(self, audio_path, target_sr=16000):
        y, sr = librosa.load(audio_path, sr=target_sr)
        reduced_noise = nr.reduce_noise(y=y, sr=sr)
        return reduced_noise, sr

    def chunk_audio(self, audio_array, sr, chunk_length_sec=60):
        chunk_size = chunk_length_sec * sr
        total_chunks = int(np.ceil(len(audio_array) / chunk_size))
        chunks = [audio_array[i * chunk_size: (i + 1) * chunk_size] for i in range(total_chunks)]
        return chunks

    def transcribe_chunk(self, chunk, sr):
        input_values = self.processor(chunk, sampling_rate=sr, return_tensors="pt", padding=True).input_values
        with torch.no_grad():
            logits = self.model(input_values).logits
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.processor.decode(predicted_ids[0])
        return transcription.lower()

    def transcribe(self, audio_path):
        print(f"Preprocessing: {audio_path}")
        audio_array, sr = self.preprocess_audio(audio_path)

        print("Chunking audio...")
        chunks = self.chunk_audio(audio_array, sr)

        print(f"Transcribing {len(chunks)} chunks in parallel...")
        transcriptions = []

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.transcribe_chunk, chunk, sr) for chunk in chunks]
            for future in tqdm(futures):
                try:
                    result = future.result()
                    transcriptions.append(result)
                except Exception as e:
                    print(f"Error in chunk transcription: {e}")

        final_transcription = " ".join(transcriptions).strip()
        print("Transcription completed.")
        return final_transcription



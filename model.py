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
import time

# Set up Hugging Face cache location - can be configured via env var
os.environ['TRANSFORMERS_CACHE'] = os.environ.get('TRANSFORMERS_CACHE', './model_cache')
os.makedirs(os.environ['TRANSFORMERS_CACHE'], exist_ok=True)
print(f"Using model cache at: {os.environ['TRANSFORMERS_CACHE']}")

# Configure torch to use smaller data types when possible
torch.set_float32_matmul_precision('medium')

class SpeechToTextModel:
    def __init__(self):
        print("SpeechToTextModel initialized - model will be loaded on first use")
        self.processor = None
        self.model = None
        self._model_loaded = False
        
        # Set model name and allow overriding via env var for smaller models if needed
        self.model_name = os.environ.get("STT_MODEL", "facebook/wav2vec2-base-960h")
        print(f"Will use model: {self.model_name}")

    def _load_model(self):
        """Lazy-load the model when actually needed"""
        if not self._model_loaded:
            try:
                print(f"Loading model ({self.model_name})...")
                start_time = time.time()
                
                # Load the processor and model with explicit caching
                self.processor = Wav2Vec2Processor.from_pretrained(
                    self.model_name,
                    cache_dir=os.environ['TRANSFORMERS_CACHE'],
                    local_files_only=os.environ.get('LOCAL_FILES_ONLY', 'False').lower() == 'true'
                )
                
                # Use half-precision when possible to reduce memory usage
                self.model = Wav2Vec2ForCTC.from_pretrained(
                    self.model_name,
                    cache_dir=os.environ['TRANSFORMERS_CACHE'],
                    local_files_only=os.environ.get('LOCAL_FILES_ONLY', 'False').lower() == 'true',
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
                )
                
                self.model.eval()
                self._model_loaded = True
                
                # Free up memory
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    
                print(f"Model loaded successfully in {time.time() - start_time:.2f} seconds")
            except Exception as e:
                print(f"Error loading model: {e}")
                raise

    def preprocess_audio(self, audio_path, target_sr=16000):
        try:
            print(f"Loading audio file: {audio_path}")
            y, sr = librosa.load(audio_path, sr=target_sr)
            
            # Reduce noise only if audio is not too short
            if len(y) > sr:  # More than 1 second
                print("Applying noise reduction")
                reduced_noise = nr.reduce_noise(y=y, sr=sr)
                return reduced_noise, sr
            else:
                print("Audio too short for noise reduction, skipping")
                return y, sr
        except Exception as e:
            print(f"Error preprocessing audio: {e}")
            raise

    def chunk_audio(self, audio_array, sr, chunk_length_sec=30):  # Reduced chunk size
        chunk_size = chunk_length_sec * sr
        total_chunks = int(np.ceil(len(audio_array) / chunk_size))
        chunks = [audio_array[i * chunk_size: (i + 1) * chunk_size] for i in range(total_chunks)]
        print(f"Split audio into {len(chunks)} chunks of {chunk_length_sec}s each")
        return chunks

    def transcribe_chunk(self, chunk, sr):
        self._load_model()  # Ensure model is loaded
        
        # Process chunk with error handling
        try:
            input_values = self.processor(chunk, sampling_rate=sr, return_tensors="pt", padding=True).input_values
            
            # Use smaller batches and free memory quickly
            with torch.no_grad():
                logits = self.model(input_values).logits
                predicted_ids = torch.argmax(logits, dim=-1)
                del logits  # Free memory immediately
                
            transcription = self.processor.decode(predicted_ids[0])
            del predicted_ids  # Free memory
            
            return transcription.lower()
        except Exception as e:
            print(f"Error in chunk transcription: {str(e)}")
            return ""  # Return empty string on error instead of crashing

    def transcribe(self, audio_path):
        try:
            print(f"Preprocessing: {audio_path}")
            audio_array, sr = self.preprocess_audio(audio_path)

            print("Chunking audio...")
            chunks = self.chunk_audio(audio_array, sr)

            print(f"Transcribing {len(chunks)} chunks in parallel...")
            
            # Use optimized processing based on chunk count
            if len(chunks) <= 3:
                print("Using sequential processing for small audio")
                transcriptions = [self.transcribe_chunk(chunk, sr) for chunk in chunks]
            else:
                # Load model once before parallel processing
                self._load_model()
                
                # Use fewer workers to avoid memory issues
                max_workers = min(4, len(chunks))
                print(f"Using ThreadPoolExecutor with {max_workers} workers")
                
                transcriptions = []
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(self.transcribe_chunk, chunk, sr) for chunk in chunks]
                    for future in tqdm(futures):
                        try:
                            result = future.result()
                            transcriptions.append(result)
                        except Exception as e:
                            print(f"Error in chunk transcription: {e}")
                            transcriptions.append("")  # Add empty string to maintain order

            final_transcription = " ".join(transcriptions).strip()
            print(f"Transcription completed. Length: {len(final_transcription)} characters")
            return final_transcription
        except Exception as e:
            print(f"Transcription failed: {e}")
            return f"Error: {str(e)}"


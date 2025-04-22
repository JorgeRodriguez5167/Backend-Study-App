from faster_whisper import WhisperModel
import os
import wave
import time

class SpeechToTextModel:
    def __init__(self, model_size_or_path="base"):
        device = "cpu"
        compute_type = "int8"
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
                compute_type = "float16"
        except ImportError:
            if os.environ.get("CUDA_VISIBLE_DEVICES") not in [None, "", "-1"]:
                device = "cuda"
                compute_type = "float16"
        self.model = WhisperModel(model_size_or_path, device=device, compute_type=compute_type)
        print(f"[INFO] Loaded Whisper model '{model_size_or_path}' on {device} with compute_type={compute_type}")

    def _gen_transcription(self, file_path: str):
        try:
            wf = wave.open(file_path, 'rb')
            frame_rate = wf.getframerate()
            n_frames = wf.getnframes()
            duration = n_frames / float(frame_rate)
            wf.close()
        except Exception as e:
            print(f"[ERROR] Failed to open audio file for duration: {e}")
            duration = 0.0

        if duration > 60:
            print(f"[DEBUG] Audio duration {duration:.2f}s exceeds 60s, using chunked transcription")
            chunk_length = 30.0  # seconds
            overlap = 5.0
            chunk_frames = int(chunk_length * frame_rate)
            overlap_frames = int(overlap * frame_rate)
            step_frames = chunk_frames - overlap_frames

            last_chunk_output = ""
            start_frame = 0
            chunk_index = 0

            wf = wave.open(file_path, 'rb')
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()

            while start_frame < n_frames:
                end_frame = min(start_frame + chunk_frames, n_frames)
                wf.setpos(start_frame)
                frames = wf.readframes(end_frame - start_frame)

                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_chunk:
                    chunk_path = tmp_chunk.name

                chunk_wav = wave.open(chunk_path, 'wb')
                chunk_wav.setnchannels(channels)
                chunk_wav.setsampwidth(sampwidth)
                chunk_wav.setframerate(frame_rate)
                chunk_wav.writeframes(frames)
                chunk_wav.close()

                segments, _ = self.model.transcribe(chunk_path)
                chunk_text = " ".join([segment.text for segment in segments])

                try:
                    os.remove(chunk_path)
                except OSError:
                    pass

                if chunk_index > 0 and last_chunk_output:
                    overlap_text = ""
                    max_overlap_len = min(len(last_chunk_output), len(chunk_text))
                    for L in range(max_overlap_len, 0, -1):
                        if last_chunk_output.endswith(chunk_text[:L]):
                            overlap_text = chunk_text[:L]
                            break
                    overlap_len = len(overlap_text) if overlap_text else 0
                else:
                    overlap_len = 0

                print(f"[DEBUG] Processed chunk {chunk_index+1}: time {start_frame/frame_rate:.2f}-{end_frame/frame_rate:.2f}s, text length {len(chunk_text)} chars")

                skipped = 0
                for segment in segments:
                    seg_text = segment.text
                    if skipped < overlap_len:
                        if len(seg_text) <= (overlap_len - skipped):
                            skipped += len(seg_text)
                            continue
                        else:
                            seg_text = seg_text[(overlap_len - skipped):]
                            skipped = overlap_len
                    if seg_text:
                        yield seg_text + " "

                last_chunk_output = chunk_text[overlap_len:] if overlap_len > 0 else chunk_text
                chunk_index += 1
                if end_frame >= n_frames:
                    break
                start_frame += step_frames

            wf.close()

        else:
            segments, _ = self.model.transcribe(file_path)
            for segment in segments:
                yield segment.text + " "

    def transcribe(self, file_path: str, preview_chars: int = 10000):
        """ Returns a tuple: (preview text, full transcription) """
        collected = []
        preview = ""
        total_chars = 0
        for text_part in self._gen_transcription(file_path):
            collected.append(text_part)
            if len(preview) < preview_chars:
                preview += text_part
            total_chars += len(text_part)

        full = "".join(collected).strip()
        return preview.strip(), full

    def transcribe_stream(self, file_path: str):
        for text_part in self._gen_transcription(file_path):
            yield text_part

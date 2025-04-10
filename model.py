from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import torch
import torchaudio

class SpeechToTextModel:
    def __init__(self):
        print(" Loading model (facebook/wav2vec2-large-960h-lv60-self)...")
        self.processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-large-960h-lv60-self")
        self.model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-large-960h-lv60-self")
        print(" Model ready.")

    def transcribe(self, file_path):
        waveform, sample_rate = torchaudio.load(file_path)

        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
            waveform = resampler(waveform)

        input_values = self.processor(waveform.squeeze(), sampling_rate=16000, return_tensors="pt").input_values
        with torch.no_grad():
            logits = self.model(input_values).logits

        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.processor.batch_decode(predicted_ids)[0]

        return transcription
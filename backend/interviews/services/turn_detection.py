''' Detect speech and conversational turn completion for live microphone input. '''

import numpy as np
import onnxruntime as ort
import torch
from huggingface_hub import hf_hub_download
from silero_vad import get_speech_timestamps, load_silero_vad
from transformers import WhisperFeatureExtractor

SMART_TURN_MODEL = 'pipecat-ai/smart-turn-v3'
SMART_TURN_FILE = 'smart-turn-v3.2-gpu.onnx'
SMART_TURN_DEVICE = 1
SMART_TURN_SECONDS = 8
SMART_TURN_THRESHOLD = 0.5
VAD_THRESHOLD = 0.5
MIN_SPEECH_MS = 250

class TurnDetector:
    ''' Reject non-speech with Silero and classify conversational turn completion with Smart Turn v3.2. '''
    def __init__(self):
        ''' Keep Silero on CPU and Smart Turn v3.2 resident on GPU 1 during live interviews. '''
        self.vad = load_silero_vad()
        self.feature_extractor = WhisperFeatureExtractor(chunk_length=SMART_TURN_SECONDS)
        model_path = hf_hub_download(repo_id=SMART_TURN_MODEL, filename=SMART_TURN_FILE)
        session_options = ort.SessionOptions()
        session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        session_options.inter_op_num_threads = 1
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        providers = [('CUDAExecutionProvider', {'device_id': SMART_TURN_DEVICE}), 'CPUExecutionProvider']
        self.smart_turn = ort.InferenceSession(model_path, sess_options=session_options, providers=providers)

    def has_speech(self, audio, sample_rate):
        ''' Return whether Silero finds a meaningful speech region in one browser audio segment. '''
        waveform = torch.from_numpy(audio)
        timestamps = get_speech_timestamps(waveform, self.vad, sampling_rate=sample_rate, threshold=VAD_THRESHOLD,
            min_speech_duration_ms=MIN_SPEECH_MS)
        return bool(timestamps)

    def completion_probability(self, audio, sample_rate):
        ''' Return Smart Turn's probability that the candidate has yielded the conversational turn. '''
        max_samples = SMART_TURN_SECONDS * sample_rate

        if audio.size > max_samples:
            audio = audio[-max_samples:]
        elif audio.size < max_samples:
            audio = np.pad(audio, (max_samples - audio.size, 0))

        inputs = self.feature_extractor(audio, sampling_rate=sample_rate, return_tensors='np', padding='max_length', max_length=max_samples,
            truncation=True, do_normalize=True)
        input_features = np.expand_dims(inputs.input_features.squeeze(0).astype(np.float32), axis=0)
        outputs = self.smart_turn.run(None, {'input_features': input_features})
        return float(outputs[0][0].item())

    def turn_complete(self, audio, sample_rate):
        ''' Return whether Smart Turn considers the accumulated candidate speech complete enough for interviewer handoff. '''
        return self.completion_probability(audio, sample_rate) > SMART_TURN_THRESHOLD

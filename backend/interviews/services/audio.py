''' Decode browser-recorded audio into mono PCM for speech recognition. '''
import subprocess

import numpy as np

def decode_browser_audio(audio_bytes):
    ''' Decode browser audio bytes into 16 kHz floating-point samples. '''
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', 'pipe:0', '-f', 's16le', '-acodec', 'pcm_s16le',
        '-ac', '1', '-ar', '16000', 'pipe:1'
    ]
    process = subprocess.run(command, input=audio_bytes, capture_output=True, check=False)

    if process.returncode != 0:
        return np.array([], dtype=np.float32), 16000

    audio = np.frombuffer(process.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return audio, 16000

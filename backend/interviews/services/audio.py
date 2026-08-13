''' Decode browser-recorded audio into mono PCM for speech recognition. '''

import subprocess

import numpy as np

MAX_AUDIO_SECONDS = 600
FFMPEG_TIMEOUT_SECONDS = 60

def decode_browser_audio(audio_bytes):
    ''' Decode browser audio bytes into 16 kHz floating-point samples. '''
    command = [
        'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-protocol_whitelist', 'pipe', '-i', 'pipe:0',
        '-t', str(MAX_AUDIO_SECONDS),
        '-f', 's16le', '-acodec', 'pcm_s16le', '-ac', '1', '-ar', '16000', 'pipe:1'
    ]

    try:
        process = subprocess.run(command, input=audio_bytes, capture_output=True, check=False, timeout=FFMPEG_TIMEOUT_SECONDS)

    except (OSError, subprocess.TimeoutExpired):
        return np.array([], dtype=np.float32), 16000

    if process.returncode != 0:
        return np.array([], dtype=np.float32), 16000

    audio = np.frombuffer(process.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return audio, 16000

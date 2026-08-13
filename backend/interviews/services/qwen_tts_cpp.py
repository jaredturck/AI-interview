''' Bind Qwen3-TTS 1.7B CustomVoice through the qwentts.cpp shared C ABI. '''

import ctypes, os
from pathlib import Path

import numpy as np

QWENTTS_ABI_VERSION = 4
QWENTTS_CACHE = Path.home() / '.cache' / 'adaptive-ai-interviewer'
QWENTTS_LIBRARY = QWENTTS_CACHE / 'qwentts.cpp' / 'build' / 'libqwen.so'
QWENTTS_MODEL_DIR = QWENTTS_CACHE / 'qwen3-tts'
QWENTTS_TALKER = QWENTTS_MODEL_DIR / 'qwen-talker-1.7b-customvoice-BF16.gguf'
QWENTTS_CODEC = QWENTTS_MODEL_DIR / 'qwen-tokenizer-12hz-BF16.gguf'
QWENTTS_BACKEND = 'CUDA0'

class QTAudio(ctypes.Structure):
    ''' Match qwentts.cpp qt_audio ABI version 4. '''
    _fields_ = [
        ('samples', ctypes.POINTER(ctypes.c_float)),
        ('n_samples', ctypes.c_int),
        ('sample_rate', ctypes.c_int),
        ('channels', ctypes.c_int)
    ]

class QTInitParams(ctypes.Structure):
    ''' Match qwentts.cpp qt_init_params ABI version 4. '''
    _fields_ = [
        ('abi_version', ctypes.c_int),
        ('talker_path', ctypes.c_char_p),
        ('codec_path', ctypes.c_char_p),
        ('use_fa', ctypes.c_bool),
        ('clamp_fp16', ctypes.c_bool),
        ('max_batch', ctypes.c_int),
        ('codec_chunk_sec', ctypes.c_float)
    ]

class QTTTSParams(ctypes.Structure):
    ''' Match qwentts.cpp qt_tts_params ABI version 4. '''
    _fields_ = [
        ('abi_version', ctypes.c_int),
        ('text', ctypes.c_char_p),
        ('lang', ctypes.c_char_p),
        ('instruct', ctypes.c_char_p),
        ('speaker', ctypes.c_char_p),
        ('ref_audio_24k', ctypes.POINTER(ctypes.c_float)),
        ('ref_n_samples', ctypes.c_int),
        ('ref_text', ctypes.c_char_p),
        ('seed', ctypes.c_int64),
        ('max_new_tokens', ctypes.c_int),
        ('do_sample', ctypes.c_bool),
        ('temperature', ctypes.c_float),
        ('top_k', ctypes.c_int),
        ('top_p', ctypes.c_float),
        ('repetition_penalty', ctypes.c_float),
        ('subtalker_do_sample', ctypes.c_bool),
        ('subtalker_temperature', ctypes.c_float),
        ('subtalker_top_k', ctypes.c_int),
        ('subtalker_top_p', ctypes.c_float),
        ('dump_dir', ctypes.c_char_p),
        ('cancel', ctypes.c_void_p),
        ('cancel_user_data', ctypes.c_void_p),
        ('on_chunk', ctypes.c_void_p),
        ('on_chunk_user_data', ctypes.c_void_p),
        ('ref_spk_emb', ctypes.POINTER(ctypes.c_float)),
        ('ref_spk_dim', ctypes.c_int),
        ('ref_codes', ctypes.POINTER(ctypes.c_int32)),
        ('ref_T', ctypes.c_int)
    ]

class QwenTTSModel:
    ''' Keep qwentts.cpp and the source-faithful Qwen3-TTS 1.7B CustomVoice GGUF resident on CUDA 0. '''
    def __init__(self):
        ''' Load the native library and initialise the fixed CustomVoice talker and codec. '''
        if not QWENTTS_LIBRARY.is_file():
            raise FileNotFoundError(f'qwentts.cpp shared library not found: {QWENTTS_LIBRARY}')

        if not QWENTTS_TALKER.is_file():
            raise FileNotFoundError(f'Qwen3-TTS talker GGUF not found: {QWENTTS_TALKER}')

        if not QWENTTS_CODEC.is_file():
            raise FileNotFoundError(f'Qwen3-TTS codec GGUF not found: {QWENTTS_CODEC}')

        self.library = ctypes.CDLL(str(QWENTTS_LIBRARY))
        self.configure_library()
        self.context = self.load_context()

    def configure_library(self):
        ''' Declare the small qwentts.cpp ABI surface used by the application. '''
        self.library.qt_init.argtypes = [ctypes.POINTER(QTInitParams)]
        self.library.qt_init.restype = ctypes.c_void_p
        self.library.qt_free.argtypes = [ctypes.c_void_p]
        self.library.qt_free.restype = None
        self.library.qt_synthesize.argtypes = [ctypes.c_void_p, ctypes.POINTER(QTTTSParams), ctypes.POINTER(QTAudio)]
        self.library.qt_synthesize.restype = ctypes.c_int
        self.library.qt_audio_free.argtypes = [ctypes.POINTER(QTAudio)]
        self.library.qt_audio_free.restype = None
        self.library.qt_last_error.argtypes = []
        self.library.qt_last_error.restype = ctypes.c_char_p

    def load_context(self):
        ''' Initialise qwentts.cpp on CUDA 0 without changing the process-wide Python model stack. '''
        params = QTInitParams(
            abi_version=QWENTTS_ABI_VERSION,
            talker_path=str(QWENTTS_TALKER).encode(),
            codec_path=str(QWENTTS_CODEC).encode(),
            use_fa=True,
            clamp_fp16=False,
            max_batch=1,
            codec_chunk_sec=24.0
        )
        previous_backend = os.environ.get('GGML_BACKEND')
        os.environ['GGML_BACKEND'] = QWENTTS_BACKEND
        context = self.library.qt_init(ctypes.byref(params))

        if previous_backend is None:
            os.environ.pop('GGML_BACKEND', None)
        else:
            os.environ['GGML_BACKEND'] = previous_backend

        if not context:
            raise RuntimeError(f'qwentts.cpp failed to initialise: {self.last_error()}')

        return context

    def last_error(self):
        ''' Return the native qwentts.cpp diagnostic for the most recent failure. '''
        message = self.library.qt_last_error()
        return message.decode(errors='replace') if message else 'Unknown qwentts.cpp error.'

    def synthesize(self, text, speaker, instruct):
        ''' Generate one English interviewer utterance as mono float PCM. '''
        params = QTTTSParams(
            abi_version=QWENTTS_ABI_VERSION,
            text=text.encode(),
            lang=b'English',
            instruct=instruct.encode(),
            speaker=speaker.encode(),
            ref_audio_24k=None,
            ref_n_samples=0,
            ref_text=None,
            seed=-1,
            max_new_tokens=2048,
            do_sample=True,
            temperature=0.9,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.05,
            subtalker_do_sample=True,
            subtalker_temperature=0.9,
            subtalker_top_k=50,
            subtalker_top_p=1.0,
            dump_dir=None,
            cancel=None,
            cancel_user_data=None,
            on_chunk=None,
            on_chunk_user_data=None,
            ref_spk_emb=None,
            ref_spk_dim=0,
            ref_codes=None,
            ref_T=0
        )
        audio = QTAudio()
        status = self.library.qt_synthesize(self.context, ctypes.byref(params), ctypes.byref(audio))

        if status != 0:
            raise RuntimeError(f'Qwen3-TTS synthesis failed: {self.last_error()}')

        sample_rate = audio.sample_rate
        samples = np.ctypeslib.as_array(audio.samples, shape=(audio.n_samples,)).copy()
        self.library.qt_audio_free(ctypes.byref(audio))
        return samples, sample_rate

    def close(self):
        ''' Release the native Qwen3-TTS model and its GGML CUDA allocations. '''
        if self.context:
            self.library.qt_free(self.context)
            self.context = None

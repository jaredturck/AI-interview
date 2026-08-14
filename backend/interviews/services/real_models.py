''' Bind the fixed Qwen interviewer, safety, speech, misuse and evaluator checkpoints to application-facing model interfaces. '''

import gc, io, re, threading

import soundfile as sf
import torch
from transformers import AutoModelForCausalLM, AutoModelForMultimodalLM, AutoProcessor, AutoTokenizer, BitsAndBytesConfig, LogitsProcessorList

from interviews.services.choice import ChoiceLogitsProcessor
from interviews.services.content import MISUSE_PROMPT
from interviews.services.evaluator_runtime import evaluate_in_worker
from interviews.services.qwen_tts_cpp import QwenTTSModel
from interviews.services.turn_detection import TurnDetector

ASR_MODEL = 'Qwen/Qwen3-ASR-1.7B-hf'
INTERVIEWER_MODEL = 'Qwen/Qwen3.5-9B'
GUARD_MODEL = 'Qwen/Qwen3Guard-Gen-4B'
MISUSE_MODEL = 'Qwen/Qwen3.5-4B'
TTS_SPEAKER = 'vivian'
TTS_INSTRUCTION = 'Speak clearly, calmly, warmly, and at a natural interview pace.'

def strip_thinking(text):
    ''' Remove Qwen thinking blocks so only candidate-facing text or stored conclusions leave the model wrapper. '''
    if '</think>' in text:
        return text.rsplit('</think>', 1)[1].strip()

    if '<think>' in text:
        return ''

    return text.strip()

def device_map_for(device):
    ''' Pin a model to one selected GPU using the Transformers root device-map format. '''
    return {'': device}

class QwenMultimodalChatModel:
    ''' Serve the realtime Qwen/Qwen3.5-9B interviewer through the shared multimodal Transformers wrapper. '''
    def __init__(self, model_name, device):
        ''' Prepare Qwen3.5-9B in INT8 on its assigned realtime GPU. '''
        model_kwargs = {
            'device_map': device_map_for(device),
            'dtype': torch.float16,
            'attn_implementation': 'sdpa',
            'low_cpu_mem_usage': True,
            'quantization_config': BitsAndBytesConfig(load_in_8bit=True)
        }
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = AutoModelForMultimodalLM.from_pretrained(model_name, **model_kwargs)
        self.model.eval()

    def prepare_inputs(self, messages, enable_thinking):
        ''' Apply the Qwen multimodal chat template with the requested thinking mode. '''
        prompt = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=enable_thinking)
        inputs = self.processor(text=[prompt], return_tensors='pt', padding=True)
        input_device = next(self.model.parameters()).device
        return inputs.to(input_device)

    def generate(self, messages, max_tokens, thinking, temperature, top_p):
        ''' Generate free-form Qwen3.5-9B interviewer text with the requested thinking mode. '''
        inputs = self.prepare_inputs(messages, thinking)

        with torch.inference_mode():
            generation = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=True, temperature=temperature,
                top_p=top_p, top_k=20, repetition_penalty=1.0)

        output = generation[0][inputs['input_ids'].shape[-1]:]
        text = self.processor.decode(output, skip_special_tokens=True)
        return strip_thinking(text)

    def choice(self, messages, choices):
        ''' Constrain Qwen3.5-9B output where application logic requires an exact approved decision. '''
        inputs = self.prepare_inputs(messages, False)
        tokenizer = self.processor.tokenizer
        choice_token_ids = [tokenizer.encode(choice, add_special_tokens=False) for choice in choices]
        logits_processor = ChoiceLogitsProcessor(inputs['input_ids'].shape[-1], choice_token_ids, tokenizer.eos_token_id)
        max_tokens = max(len(choice) for choice in choice_token_ids) + 1

        with torch.inference_mode():
            generation = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False,
                logits_processor=LogitsProcessorList([logits_processor]))

        output = generation[0][inputs['input_ids'].shape[-1]:]
        text = tokenizer.decode(output, skip_special_tokens=True).strip()
        return text if text in choices else ''

class QwenTextModel:
    ''' Serve the text-only Qwen/Qwen3.5-4B misuse monitor through Transformers. '''
    def __init__(self, model_name, device):
        ''' Keep Qwen3.5-4B in INT8 on its assigned realtime GPU for misuse classification. '''
        model_kwargs = {
            'device_map': device_map_for(device),
            'dtype': torch.float16,
            'low_cpu_mem_usage': True,
            'quantization_config': BitsAndBytesConfig(load_in_8bit=True)
        }
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
        self.model.eval()

    def prepare_inputs(self, messages, enable_thinking):
        ''' Apply the Qwen3.5 chat template for constrained misuse classification. '''
        inputs = self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_dict=True,
            return_tensors='pt', enable_thinking=enable_thinking)
        return inputs.to(self.model.device)

    def choice(self, messages, choices):
        ''' Limit misuse-monitor output to the exact control decisions understood by interview policy. '''
        inputs = self.prepare_inputs(messages, False)
        choice_token_ids = [self.tokenizer.encode(choice, add_special_tokens=False) for choice in choices]
        logits_processor = ChoiceLogitsProcessor(inputs['input_ids'].shape[-1], choice_token_ids, self.tokenizer.eos_token_id)
        max_tokens = max(len(choice) for choice in choice_token_ids) + 1

        with torch.inference_mode():
            generation = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False,
                logits_processor=LogitsProcessorList([logits_processor]))

        output = generation[0][inputs['input_ids'].shape[-1]:]
        text = self.tokenizer.decode(output, skip_special_tokens=True).strip()
        return text if text in choices else ''

class QwenASRModel:
    ''' Transcribe candidate speech with Qwen/Qwen3-ASR-1.7B-hf while allowing automatic language detection. '''
    def __init__(self):
        ''' Keep Qwen3-ASR-1.7B-hf resident in BF16 on GPU 1 for realtime speech input. '''
        self.processor = AutoProcessor.from_pretrained(ASR_MODEL)
        self.model = AutoModelForMultimodalLM.from_pretrained(ASR_MODEL, device_map=device_map_for('cuda:1'), dtype=torch.bfloat16,
            attn_implementation='sdpa', low_cpu_mem_usage=True)
        self.model.eval()

    def transcribe(self, audio, sample_rate):
        ''' Convert one candidate utterance into interview text while Qwen3-ASR detects the spoken language. '''
        inputs = self.processor.apply_transcription_request(audio=audio)
        inputs = inputs.to(next(self.model.parameters()).device, self.model.dtype)

        with torch.inference_mode():
            generation = self.model.generate(**inputs, max_new_tokens=512, do_sample=False)

        output = generation[:, inputs['input_ids'].shape[-1]:]
        return self.processor.decode(output, return_format='transcription_only')[0].strip()

class QwenGuardModel:
    ''' Protect candidate input and interviewer output with Qwen/Qwen3Guard-Gen-4B. '''
    def __init__(self):
        ''' Keep Qwen3Guard-Gen-4B resident in INT8 on GPU 1 for realtime safety checks. '''
        model_kwargs = {
            'device_map': device_map_for('cuda:1'),
            'dtype': torch.float16,
            'low_cpu_mem_usage': True,
            'quantization_config': BitsAndBytesConfig(load_in_8bit=True)
        }
        self.tokenizer = AutoTokenizer.from_pretrained(GUARD_MODEL)
        self.model = AutoModelForCausalLM.from_pretrained(GUARD_MODEL, **model_kwargs)
        self.model.eval()

    def classify(self, messages):
        ''' Reduce Qwen3Guard output to the Safe, Unsafe or Controversial label required by interview control. '''
        text = self.tokenizer.apply_chat_template(messages, tokenize=False)
        inputs = self.tokenizer([text], return_tensors='pt').to(self.model.device)

        with torch.inference_mode():
            generated = self.model.generate(**inputs, max_new_tokens=48, do_sample=False)

        output = generated[0][inputs['input_ids'].shape[-1]:]
        content = self.tokenizer.decode(output, skip_special_tokens=True)
        match = re.search(r'Safety:\s*(Safe|Unsafe|Controversial)', content)
        return match.group(1) if match else 'Unsafe'

def load_qwen_tts():
    ''' Keep Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice on GPU 0 through the qwentts.cpp native runtime. '''
    return QwenTTSModel()

class RealModelSuite:
    ''' Own the realtime Qwen stack, turn detector and isolated Qwen3.6 evaluator lifecycle. '''
    def __init__(self):
        ''' Track model residency and serialize realtime/evaluator GPU ownership transitions. '''
        self.lock = threading.RLock()
        self.asr = None
        self.tts = None
        self.turn_detector = None
        self.interviewer_model = None
        self.misuse_model = None
        self.guard_model = None
        self.mode = 'idle'

    def clear_cuda(self):
        ''' Reclaim GPU memory after switching between the realtime Qwen stack and Qwen3.6 evaluation. '''
        gc.collect()
        torch.cuda.empty_cache()

    def load_live(self):
        ''' Make the realtime speech, turn-detection, safety and interviewer stack resident for immediate interviews. '''
        with self.lock:
            if self.mode == 'live' and self.interviewer_model:
                return

            self.unload_evaluator()
            print('Loading Qwen3-TTS realtime model...', flush=True)
            self.tts = load_qwen_tts()
            print('Loading Qwen3-ASR realtime model...', flush=True)
            self.asr = QwenASRModel()
            print('Loading Silero VAD and Smart Turn v3.2 realtime models...', flush=True)
            self.turn_detector = TurnDetector()
            print('Loading Qwen3Guard realtime model...', flush=True)
            self.guard_model = QwenGuardModel()
            print('Loading Qwen3.5-4B misuse model...', flush=True)
            self.misuse_model = QwenTextModel(MISUSE_MODEL, 'cuda:1')
            print('Loading Qwen3.5-9B interviewer model...', flush=True)
            self.interviewer_model = QwenMultimodalChatModel(INTERVIEWER_MODEL, 'cuda:0')
            self.mode = 'live'

    def live_loaded(self):
        ''' Gate interview availability on every required realtime model being resident. '''
        return self.mode == 'live' and all([self.asr, self.tts, self.turn_detector, self.interviewer_model, self.misuse_model, self.guard_model])

    def unload_live(self):
        ''' Free both GPUs for Qwen3.6 final evaluation by releasing the realtime model stack. '''
        with self.lock:
            self.asr = None

            if self.tts:
                self.tts.close()

            self.tts = None
            self.turn_detector = None
            self.interviewer_model = None
            self.misuse_model = None
            self.guard_model = None

            if self.mode == 'live':
                self.mode = 'idle'

            self.clear_cuda()

    def load_evaluator(self):
        ''' Release the realtime stack before the isolated vLLM evaluator process takes both GPUs. '''
        with self.lock:
            if self.mode == 'evaluator':
                return

            self.unload_live()
            self.mode = 'evaluator'

    def unload_evaluator(self):
        ''' Return parent-process runtime state to idle after the isolated evaluator process exits. '''
        with self.lock:
            if self.mode == 'evaluator':
                self.mode = 'idle'

            self.clear_cuda()

    def has_speech(self, audio, sample_rate):
        ''' Reject browser audio segments that do not contain meaningful human speech. '''
        return self.turn_detector.has_speech(audio, sample_rate)

    def turn_complete(self, audio, sample_rate):
        ''' Decide whether accumulated candidate speech has reached a conversational handoff point. '''
        return self.turn_detector.turn_complete(audio, sample_rate)

    def transcribe(self, audio, sample_rate):
        ''' Expose Qwen3-ASR transcription through the model-suite interface used by live WebSocket interviews. '''
        return self.asr.transcribe(audio, sample_rate)

    def speak(self, text):
        ''' Turn interviewer text into WAV bytes with Qwen3-TTS for direct WebSocket delivery. '''
        wav, sample_rate = self.tts.synthesize(text, TTS_SPEAKER, TTS_INSTRUCTION)
        output = io.BytesIO()
        sf.write(output, wav, sample_rate, format='WAV')
        return output.getvalue()

    def guard_user(self, text):
        ''' Block unsafe candidate requests before they reach the Qwen3.5 interviewer. '''
        return self.guard_model.classify([{'role': 'user', 'content': text}])

    def guard_response(self, user_text, assistant_text):
        ''' Block unsafe Qwen3.5 interviewer output before it is shown or synthesized. '''
        return self.guard_model.classify([
            {'role': 'user', 'content': user_text},
            {'role': 'assistant', 'content': assistant_text}
        ])

    def interviewer(self, system_prompt, turns, max_tokens=32):
        ''' Use Qwen3.5-9B without thinking to generate the next short adaptive interview turn. '''
        messages = [{'role': 'system', 'content': system_prompt}]
        messages.extend({'role': turn['role'], 'content': turn['text']} for turn in turns)
        return self.interviewer_model.generate(messages, max_tokens=max_tokens, thinking=False, temperature=0.7, top_p=0.8)

    def job_metadata(self, description):
        ''' Extract a short job title and optional subtitle from the staff-authored vacancy description. '''
        system_prompt = ('Extract concise UI metadata from the job description. Return JSON only with keys title and subtitle. '
            'Keep the title to roughly two to four words, keep the subtitle short and optional, and do not invent unsupported details.')
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': description}
        ]
        return self.interviewer_model.generate(messages, max_tokens=80, thinking=False, temperature=0.2, top_p=0.8)

    def misuse(self, transcript):
        ''' Use Qwen3.5-4B to decide whether accumulated misuse should continue, redirect or terminate the interview. '''
        messages = [
            {'role': 'system', 'content': MISUSE_PROMPT},
            {'role': 'user', 'content': transcript}
        ]
        return self.misuse_model.choice(messages, ['CONTINUE', 'REDIRECT', 'TERMINATE'])

    def evaluate(self, job_description, transcript, questions):
        ''' Run the complete Qwen3.6 evaluation workload in one isolated, batched vLLM process. '''
        self.load_evaluator()
        return evaluate_in_worker(job_description, transcript, questions)

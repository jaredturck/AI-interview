''' Real Qwen model implementations for interview inference. '''

import gc, io, re, threading

import soundfile as sf
import torch
from transformers import AutoModelForCausalLM, AutoModelForMultimodalLM, AutoProcessor, AutoTokenizer, BitsAndBytesConfig, LogitsProcessorList

from interviews.services.choice import ChoiceLogitsProcessor
from interviews.services.content import EVALUATOR_QUESTION_PROMPT, FINAL_CHOICE_PROMPT, FINAL_OUTPUT_PROMPT, MISUSE_PROMPT

ASR_MODEL = 'Qwen/Qwen3-ASR-1.7B-hf'
INTERVIEWER_MODEL = 'Qwen/Qwen3.5-9B'
TTS_MODEL = 'Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice'
GUARD_MODEL = 'Qwen/Qwen3Guard-Gen-4B'
MISUSE_MODEL = 'Qwen/Qwen3.5-4B'
EVALUATOR_MODEL = 'Qwen/Qwen3.6-27B'
TTS_SPEAKER = 'Ryan'
TTS_INSTRUCTION = 'Speak clearly, calmly, warmly, and at a natural interview pace.'
QUESTION_MAX_TOKENS = 2048
FINAL_REASONING_MAX_TOKENS = 4096

def strip_thinking(text):
    ''' Return only the final response after a model thinking block. '''
    if '</think>' in text:
        return text.rsplit('</think>', 1)[1].strip()

    if '<think>' in text:
        return ''

    return text.strip()

def device_map_for(device):
    ''' Convert one fixed device into a Transformers device map. '''
    return {'': device}

class QwenMultimodalChatModel:
    ''' Run the fixed Qwen3.5 and Qwen3.6 checkpoints through Transformers. '''
    def __init__(self, model_name, device, evaluator=False):
        ''' Load one Qwen multimodal checkpoint in INT8. '''
        model_kwargs = {
            'device_map': 'auto' if evaluator else device_map_for(device),
            'dtype': torch.bfloat16,
            'attn_implementation': 'sdpa',
            'low_cpu_mem_usage': True,
            'quantization_config': BitsAndBytesConfig(load_in_8bit=True)
        }

        if evaluator:
            model_kwargs['max_memory'] = {0: '22GiB', 1: '22GiB', 'cpu': '48GiB'}

        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = AutoModelForMultimodalLM.from_pretrained(model_name, **model_kwargs)
        self.model.eval()

    def prepare_inputs(self, messages, enable_thinking):
        ''' Tokenize text-only chat messages with the model processor. '''
        prompt = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=enable_thinking)
        inputs = self.processor(text=[prompt], return_tensors='pt', padding=True)
        input_device = next(self.model.parameters()).device
        return inputs.to(input_device)

    def generate(self, messages, max_tokens, thinking, temperature, top_p):
        ''' Generate one free-form model response. '''
        inputs = self.prepare_inputs(messages, thinking)

        with torch.inference_mode():
            generation = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=True, temperature=temperature,
                top_p=top_p, top_k=20, repetition_penalty=1.0)

        output = generation[0][inputs['input_ids'].shape[-1]:]
        text = self.processor.decode(output, skip_special_tokens=True)
        return strip_thinking(text)

    def choice(self, messages, choices):
        ''' Generate exactly one value from a fixed choice set. '''
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
    ''' Run a fixed text-only Qwen checkpoint through Transformers. '''
    def __init__(self, model_name, device):
        ''' Load one text model in INT8. '''
        model_kwargs = {
            'device_map': device_map_for(device),
            'dtype': torch.bfloat16,
            'low_cpu_mem_usage': True,
            'quantization_config': BitsAndBytesConfig(load_in_8bit=True)
        }
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
        self.model.eval()

    def prepare_inputs(self, messages, enable_thinking):
        ''' Tokenize plain text messages using the Qwen chat template. '''
        inputs = self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_dict=True,
            return_tensors='pt', enable_thinking=enable_thinking)
        return inputs.to(self.model.device)

    def choice(self, messages, choices):
        ''' Generate exactly one value from a fixed choice set. '''
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
    ''' Transcribe candidate speech with the native Hugging Face Qwen3-ASR checkpoint. '''
    def __init__(self):
        ''' Load Qwen3-ASR in BF16 on the second GPU. '''
        self.processor = AutoProcessor.from_pretrained(ASR_MODEL)
        self.model = AutoModelForMultimodalLM.from_pretrained(ASR_MODEL, device_map=device_map_for('cuda:1'), dtype=torch.bfloat16,
            attn_implementation='sdpa', low_cpu_mem_usage=True)
        self.model.eval()

    def transcribe(self, audio, sample_rate):
        ''' Transcribe one mono candidate utterance with automatic language detection. '''
        inputs = self.processor.apply_transcription_request(audio=(audio, sample_rate))
        inputs = inputs.to(next(self.model.parameters()).device)

        with torch.inference_mode():
            generation = self.model.generate(**inputs, max_new_tokens=512, do_sample=False)

        output = generation[0][inputs['input_ids'].shape[-1]:]
        text = self.processor.decode(output, skip_special_tokens=True).strip()
        match = re.search(r'<asr_text>(.*?)</asr_text>', text, flags=re.DOTALL)
        return match.group(1).strip() if match else text

class QwenGuardModel:
    ''' Run Qwen3Guard content-safety classification. '''
    def __init__(self):
        ''' Load Qwen3Guard in INT8 on the second GPU. '''
        model_kwargs = {
            'device_map': device_map_for('cuda:1'),
            'dtype': torch.bfloat16,
            'low_cpu_mem_usage': True,
            'quantization_config': BitsAndBytesConfig(load_in_8bit=True)
        }
        self.tokenizer = AutoTokenizer.from_pretrained(GUARD_MODEL)
        self.model = AutoModelForCausalLM.from_pretrained(GUARD_MODEL, **model_kwargs)
        self.model.eval()

    def classify(self, messages):
        ''' Classify a conversation as safe, unsafe, or controversial. '''
        text = self.tokenizer.apply_chat_template(messages, tokenize=False)
        inputs = self.tokenizer([text], return_tensors='pt').to(self.model.device)

        with torch.inference_mode():
            generated = self.model.generate(**inputs, max_new_tokens=48, do_sample=False)

        output = generated[0][inputs['input_ids'].shape[-1]:]
        content = self.tokenizer.decode(output, skip_special_tokens=True)
        match = re.search(r'Safety:\s*(Safe|Unsafe|Controversial)', content)
        return match.group(1) if match else 'Unsafe'

def load_qwen_tts():
    ''' Load the fixed Qwen3-TTS model for realtime interviews. '''
    from qwen_tts import Qwen3TTSModel  # noqa: PLC0415
    return Qwen3TTSModel.from_pretrained(TTS_MODEL, device_map='cuda:0', dtype=torch.bfloat16, attn_implementation='sdpa')

class RealModelSuite:
    ''' Coordinate the fixed Qwen models used by the three AI subsystems. '''
    def __init__(self):
        ''' Initialize model references and GPU lifecycle state. '''
        self.lock = threading.RLock()
        self.asr = None
        self.tts = None
        self.interviewer_model = None
        self.misuse_model = None
        self.guard_model = None
        self.evaluator_model = None
        self.mode = 'idle'

    def clear_cuda(self):
        ''' Release unused Python and CUDA allocations. '''
        gc.collect()
        torch.cuda.empty_cache()

    def load_live(self):
        ''' Load the realtime interviewer, speech, safety, and misuse models. '''
        with self.lock:
            if self.mode == 'live' and self.interviewer_model:
                return

            self.unload_evaluator()
            self.interviewer_model = QwenMultimodalChatModel(INTERVIEWER_MODEL, 'cuda:0')
            self.misuse_model = QwenTextModel(MISUSE_MODEL, 'cuda:1')
            self.guard_model = QwenGuardModel()
            self.asr = QwenASRModel()
            self.tts = load_qwen_tts()
            self.mode = 'live'

    def live_loaded(self):
        ''' Return whether every realtime model is resident and ready. '''
        return self.mode == 'live' and all([self.asr, self.tts, self.interviewer_model, self.misuse_model, self.guard_model])

    def unload_live(self):
        ''' Unload all realtime models from GPU memory. '''
        with self.lock:
            self.asr = None
            self.tts = None
            self.interviewer_model = None
            self.misuse_model = None
            self.guard_model = None

            if self.mode == 'live':
                self.mode = 'idle'

            self.clear_cuda()

    def load_evaluator(self):
        ''' Give both GPUs to the extended-reasoning evaluator. '''
        with self.lock:
            if self.mode == 'evaluator' and self.evaluator_model:
                return

            self.unload_live()
            self.evaluator_model = QwenMultimodalChatModel(EVALUATOR_MODEL, 'cuda:0', evaluator=True)
            self.mode = 'evaluator'

    def unload_evaluator(self):
        ''' Unload the final evaluator from GPU memory. '''
        with self.lock:
            self.evaluator_model = None

            if self.mode == 'evaluator':
                self.mode = 'idle'

            self.clear_cuda()

    def transcribe(self, audio, sample_rate):
        ''' Transcribe candidate speech with automatic language detection. '''
        return self.asr.transcribe(audio, sample_rate)

    def speak(self, text):
        ''' Synthesize one short interviewer response as WAV audio. '''
        wavs, sample_rate = self.tts.generate_custom_voice(text=text, language='Auto', speaker=TTS_SPEAKER, instruct=TTS_INSTRUCTION)
        output = io.BytesIO()
        sf.write(output, wavs[0], sample_rate, format='WAV')
        return output.getvalue()

    def guard_user(self, text):
        ''' Check a candidate request before interviewer generation. '''
        return self.guard_model.classify([{'role': 'user', 'content': text}])

    def guard_response(self, user_text, assistant_text):
        ''' Check interviewer output before speech synthesis. '''
        return self.guard_model.classify([
            {'role': 'user', 'content': user_text},
            {'role': 'assistant', 'content': assistant_text}
        ])

    def interviewer(self, system_prompt, turns, max_tokens=32):
        ''' Generate the next brief realtime interviewer response. '''
        messages = [{'role': 'system', 'content': system_prompt}]
        messages.extend({'role': turn['role'], 'content': turn['text']} for turn in turns)
        return self.interviewer_model.generate(messages, max_tokens=max_tokens, thinking=False, temperature=0.7, top_p=0.8)

    def misuse(self, transcript):
        ''' Classify accumulated interview misuse as continue, redirect, or terminate. '''
        messages = [
            {'role': 'system', 'content': MISUSE_PROMPT},
            {'role': 'user', 'content': transcript}
        ]
        return self.misuse_model.choice(messages, ['CONTINUE', 'REDIRECT', 'TERMINATE'])

    def evaluate_question(self, job_description, transcript, question):
        ''' Reason deeply about one fixed evaluation criterion. '''
        self.load_evaluator()
        context = f'JOB DESCRIPTION\n{job_description}\n\nINTERVIEW TRANSCRIPT\n{transcript}\n\nCRITERION\n{question}'
        messages = [
            {'role': 'system', 'content': EVALUATOR_QUESTION_PROMPT},
            {'role': 'user', 'content': context}
        ]
        return self.evaluator_model.generate(messages, max_tokens=QUESTION_MAX_TOKENS, thinking=True, temperature=1.0, top_p=0.95)

    def final_choice(self, job_description, transcript, answers):
        ''' Reason across all criterion assessments before producing the constrained outcome. '''
        self.load_evaluator()
        assessments = '\n\n'.join(f'{index + 1}. {item["question"]}\nAssessment: {item["answer"]}' for index, item in enumerate(answers))
        context = f'JOB DESCRIPTION\n{job_description}\n\nINTERVIEW TRANSCRIPT\n{transcript}\n\nCRITERION ASSESSMENTS\n{assessments}'
        reasoning_messages = [
            {'role': 'system', 'content': FINAL_CHOICE_PROMPT},
            {'role': 'user', 'content': context}
        ]
        decision_analysis = self.evaluator_model.generate(reasoning_messages, max_tokens=FINAL_REASONING_MAX_TOKENS, thinking=True,
            temperature=1.0, top_p=0.95)
        choice_messages = [
            {'role': 'system', 'content': FINAL_OUTPUT_PROMPT},
            {'role': 'user', 'content': f'{context}\n\nFINAL DECISION ANALYSIS\n{decision_analysis}'}
        ]
        return self.evaluator_model.choice(choice_messages, ['PROGRESS', 'NOT_PROGRESS'])

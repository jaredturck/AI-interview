''' Bind the fixed Qwen interview, safety, speech, misuse and evaluation checkpoints to application-facing model interfaces. '''

import io, re, threading, time

import soundfile as sf
import torch
from transformers import AutoModelForCausalLM, AutoModelForMultimodalLM, AutoProcessor, AutoTokenizer, BitsAndBytesConfig, LogitsProcessorList, Qwen3_5ForCausalLM
from transformers.utils.import_utils import is_causal_conv1d_available, is_flash_linear_attention_available

from interviews.services.choice import ChoiceLogitsProcessor
from interviews.services.content import EVALUATOR_QUESTION_PROMPT, FINAL_CHOICE_PROMPT, FINAL_OUTPUT_PROMPT, MISUSE_PROMPT
from interviews.services.qwen_tts_cpp import QwenTTSModel
from interviews.services.turn_detection import TurnDetector

ASR_MODEL = 'Qwen/Qwen3-ASR-1.7B-hf'
SHARED_MODEL = 'Qwen/Qwen3.5-9B'
GUARD_MODEL = 'Qwen/Qwen3Guard-Gen-4B'
MISUSE_MODEL = 'Qwen/Qwen3.5-4B'
SHARED_MODEL_DEVICE = 'cuda:0'
EVALUATOR_BATCH_SIZE = 2
EVALUATOR_QUESTION_MAX_TOKENS = 512
EVALUATOR_REASONING_MAX_TOKENS = 768
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

def evaluator_messages(system_prompt, context):
    ''' Build one text-only Qwen3.5-9B evaluator request using the same chat interface as live interviewing. '''
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': context}
    ]

class GenerationTimer:
    ''' Capture Qwen generation start and first-token timing without altering logits. '''
    def __init__(self, device):
        self.device = device
        self.started = time.perf_counter()
        self.first_step = None

    def __call__(self, input_ids, scores):
        if self.first_step is None:
            torch.cuda.synchronize(self.device)
            self.first_step = time.perf_counter()

        return scores

class QwenSharedModel:
    ''' Serve one permanently resident Qwen3.5-9B instance for interviewing, job metadata and final evaluation. '''
    def __init__(self):
        ''' Load Qwen3.5-9B as INT8 weights with FP16 compute entirely on GPU 0. '''
        quantization = BitsAndBytesConfig(load_in_8bit=True)
        model_kwargs = {
            'device_map': device_map_for(SHARED_MODEL_DEVICE),
            'dtype': torch.float16,
            'attn_implementation': 'sdpa',
            'low_cpu_mem_usage': True,
            'quantization_config': quantization
        }
        fast_deltanet = is_flash_linear_attention_available() and is_causal_conv1d_available()
        backend = 'FLA + causal-conv1d' if fast_deltanet else 'PyTorch fallback'
        print(f'Qwen3.5-9B DeltaNet backend: {backend}', flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(SHARED_MODEL)
        self.tokenizer.padding_side = 'left'
        self.model = Qwen3_5ForCausalLM.from_pretrained(SHARED_MODEL, **model_kwargs)
        self.model.eval()

    def input_device(self):
        ''' Return the single GPU holding the complete Qwen3.5-9B model. '''
        return self.model.get_input_embeddings().weight.device

    def log_generation(self, timer, inputs, generation, batch_size, label):
        ''' Print first-token latency and decode throughput for one Qwen3.5-9B generation call. '''
        torch.cuda.synchronize(self.input_device())
        finished = time.perf_counter()
        first_step = timer.first_step or finished
        prompt_tokens = inputs['attention_mask'].sum().item()
        generated_steps = generation.shape[-1] - inputs['input_ids'].shape[-1]
        generated_tokens = generated_steps * batch_size
        ttft = first_step - timer.started
        decode_time = max(finished - first_step, 0.000001)
        total_time = finished - timer.started
        throughput = generated_tokens / decode_time
        print(f'[Qwen3.5-9B Perf] {label}: batch={batch_size} prompt_tokens={prompt_tokens} generated_tokens={generated_tokens} '
            f'ttft={ttft:.3f}s total={total_time:.3f}s decode={throughput:.1f} tok/s', flush=True)

    def prepare_inputs(self, messages, enable_thinking):
        ''' Apply the Qwen3.5-9B chat template for one text-only request. '''
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=enable_thinking)
        inputs = self.tokenizer([prompt], return_tensors='pt', padding=True)
        return inputs.to(self.input_device())

    def prepare_batch(self, message_batches, enable_thinking):
        ''' Tokenize a small batch of independent Qwen3.5-9B evaluator requests with left padding. '''
        prompts = [self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=enable_thinking) for messages in message_batches]
        inputs = self.tokenizer(prompts, return_tensors='pt', padding=True)
        return inputs.to(self.input_device())

    def generate(self, messages, max_tokens, thinking, temperature, top_p):
        ''' Generate one free-form Qwen3.5-9B response for interviewer, metadata or evaluator reasoning. '''
        inputs = self.prepare_inputs(messages, thinking)
        timer = GenerationTimer(self.input_device())

        with torch.inference_mode():
            generation = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=True, temperature=temperature,
                top_p=top_p, top_k=20, repetition_penalty=1.0, logits_processor=LogitsProcessorList([timer]))

        self.log_generation(timer, inputs, generation, 1, 'generation')
        output = generation[0][inputs['input_ids'].shape[-1]:]
        text = self.tokenizer.decode(output, skip_special_tokens=True)
        return strip_thinking(text)

    def generate_batch(self, message_batches, max_tokens, thinking, temperature, top_p):
        ''' Generate an evaluator microbatch while keeping the shared model and auxiliary stack resident. '''
        inputs = self.prepare_batch(message_batches, thinking)
        timer = GenerationTimer(self.input_device())

        with torch.inference_mode():
            generation = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=True, temperature=temperature,
                top_p=top_p, top_k=20, repetition_penalty=1.0, logits_processor=LogitsProcessorList([timer]))

        self.log_generation(timer, inputs, generation, len(message_batches), 'evaluation batch')
        output = generation[:, inputs['input_ids'].shape[-1]:]
        texts = self.tokenizer.batch_decode(output, skip_special_tokens=True)
        return [strip_thinking(text) for text in texts]

    def choice(self, messages, choices):
        ''' Constrain Qwen3.5-9B output where application logic requires an exact approved decision. '''
        inputs = self.prepare_inputs(messages, False)
        tokenizer = self.tokenizer
        choice_token_ids = [tokenizer.encode(choice, add_special_tokens=False) for choice in choices]
        logits_processor = ChoiceLogitsProcessor(inputs['input_ids'].shape[-1], choice_token_ids, tokenizer.eos_token_id)
        max_tokens = max(len(choice) for choice in choice_token_ids) + 1

        timer = GenerationTimer(self.input_device())

        with torch.inference_mode():
            generation = self.model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False,
                logits_processor=LogitsProcessorList([timer, logits_processor]))

        self.log_generation(timer, inputs, generation, 1, 'constrained choice')
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
            'attn_implementation': 'sdpa',
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
        ''' Keep Qwen3Guard-Gen-4B resident in INT8 on GPU 1 with the auxiliary realtime models. '''
        model_kwargs = {
            'device_map': device_map_for('cuda:1'),
            'dtype': torch.float16,
            'attn_implementation': 'sdpa',
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
    ''' Own one permanently resident dual-GPU model stack shared by live interviewing and final evaluation. '''
    def __init__(self):
        ''' Track model residency while keeping all inference checkpoints alive for the lifetime of the Django worker. '''
        self.lock = threading.RLock()
        self.asr = None
        self.tts = None
        self.turn_detector = None
        self.shared_model = None
        self.misuse_model = None
        self.guard_model = None

    def load_models(self):
        ''' Load the complete interview and evaluation stack once, with Qwen3.5-9B isolated on GPU 0. '''
        with self.lock:
            if self.models_loaded():
                return

            if self.tts is None:
                print('Loading Qwen3-TTS model on GPU 0...', flush=True)
                self.tts = load_qwen_tts()

            if self.asr is None:
                print('Loading Qwen3-ASR model on GPU 1...', flush=True)
                self.asr = QwenASRModel()

            if self.turn_detector is None:
                print('Loading Silero VAD and Smart Turn v3.2 on CPU/GPU 1...', flush=True)
                self.turn_detector = TurnDetector()

            if self.guard_model is None:
                print('Loading Qwen3Guard model on GPU 1...', flush=True)
                self.guard_model = QwenGuardModel()

            if self.misuse_model is None:
                print('Loading Qwen3.5-4B misuse model on GPU 1...', flush=True)
                self.misuse_model = QwenTextModel(MISUSE_MODEL, 'cuda:1')

            if self.shared_model is None:
                print('Loading shared Qwen3.5-9B INT8 model entirely on GPU 0...', flush=True)
                self.shared_model = QwenSharedModel()

    def models_loaded(self):
        ''' Gate interview and evaluation availability on every required resident model being loaded. '''
        return all([self.asr, self.tts, self.turn_detector, self.shared_model, self.misuse_model, self.guard_model])

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
        ''' Block unsafe candidate requests before they reach the shared Qwen3.5-9B interviewer. '''
        return self.guard_model.classify([{'role': 'user', 'content': text}])

    def guard_response(self, user_text, assistant_text):
        ''' Block unsafe Qwen3.5-9B interviewer output before it is shown or synthesized. '''
        return self.guard_model.classify([
            {'role': 'user', 'content': user_text},
            {'role': 'assistant', 'content': assistant_text}
        ])

    def interviewer(self, system_prompt, turns, max_tokens=32):
        ''' Use Qwen3.5-9B without thinking to generate the next short adaptive interview turn. '''
        messages = [{'role': 'system', 'content': system_prompt}]
        messages.extend({'role': turn['role'], 'content': turn['text']} for turn in turns)
        return self.shared_model.generate(messages, max_tokens=max_tokens, thinking=False, temperature=0.7, top_p=0.8)

    def job_metadata(self, description):
        ''' Extract a short job title and optional subtitle from the staff-authored vacancy description. '''
        system_prompt = ('Extract concise UI metadata from the job description. Return JSON only with keys title and subtitle. '
            'Keep the title to roughly two to four words, keep the subtitle short and optional, and do not invent unsupported details.')
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': description}
        ]
        return self.shared_model.generate(messages, max_tokens=80, thinking=False, temperature=0.2, top_p=0.8)

    def misuse(self, transcript):
        ''' Use Qwen3.5-4B to decide whether accumulated misuse should continue, redirect or terminate the interview. '''
        messages = [
            {'role': 'system', 'content': MISUSE_PROMPT},
            {'role': 'user', 'content': transcript}
        ]
        return self.misuse_model.choice(messages, ['CONTINUE', 'REDIRECT', 'TERMINATE'])

    def evaluate(self, job_description, transcript, questions):
        ''' Evaluate every criterion and final decision with the same resident Qwen3.5-9B model used for interviewing. '''
        common_context = f'JOB DESCRIPTION\n{job_description}\n\nINTERVIEW TRANSCRIPT\n{transcript}\n\nCRITERION\n'
        question_messages = [evaluator_messages(EVALUATOR_QUESTION_PROMPT, common_context + question) for question in questions]
        answers = []

        total_batches = (len(question_messages) + EVALUATOR_BATCH_SIZE - 1) // EVALUATOR_BATCH_SIZE

        for start in range(0, len(question_messages), EVALUATOR_BATCH_SIZE):
            batch = question_messages[start:start + EVALUATOR_BATCH_SIZE]
            batch_number = start // EVALUATOR_BATCH_SIZE + 1
            started = time.perf_counter()
            print(f'Evaluation batch {batch_number}/{total_batches} started ({len(batch)} criteria).', flush=True)
            batch_answers = self.shared_model.generate_batch(batch, max_tokens=EVALUATOR_QUESTION_MAX_TOKENS, thinking=False,
                temperature=0.2, top_p=0.8)
            answers.extend(batch_answers)
            elapsed = time.perf_counter() - started
            print(f'Evaluation batch {batch_number}/{total_batches} finished in {elapsed:.1f}s; '
                f'{len(answers)}/{len(questions)} criteria complete.', flush=True)

        if len(answers) != len(questions) or any(not answer for answer in answers):
            return {'answers': answers, 'result': '', 'error': 'Qwen3.5-9B returned an incomplete criterion batch.'}

        assessments = '\n\n'.join(f'{index + 1}. {question}\nAssessment: {answers[index]}' for index, question in enumerate(questions))
        final_context = f'JOB DESCRIPTION\n{job_description}\n\nINTERVIEW TRANSCRIPT\n{transcript}\n\nCRITERION ASSESSMENTS\n{assessments}'
        reasoning_messages = evaluator_messages(FINAL_CHOICE_PROMPT, final_context)
        decision_analysis = self.shared_model.generate(reasoning_messages, max_tokens=EVALUATOR_REASONING_MAX_TOKENS, thinking=False,
            temperature=0.2, top_p=0.8)

        if not decision_analysis:
            return {'answers': answers, 'result': '', 'error': 'Qwen3.5-9B returned no final evaluation reasoning.'}

        choice_context = f'{final_context}\n\nFINAL DECISION ANALYSIS\n{decision_analysis}'
        result = self.shared_model.choice(evaluator_messages(FINAL_OUTPUT_PROMPT, choice_context), ['PROGRESS', 'NOT_PROGRESS'])

        if result not in ['PROGRESS', 'NOT_PROGRESS']:
            return {'answers': answers, 'result': '', 'error': 'Qwen3.5-9B returned an invalid final evaluation decision.'}

        return {'answers': answers, 'result': result, 'error': ''}

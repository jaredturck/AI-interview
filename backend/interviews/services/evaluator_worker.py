''' Run batched Qwen3.6 evaluation inside a clean vLLM process with both GPUs participating through tensor parallelism. '''

import gc, traceback

from tqdm import tqdm

from interviews.services.content import EVALUATOR_QUESTION_PROMPT, FINAL_CHOICE_PROMPT, FINAL_OUTPUT_PROMPT

EVALUATOR_BASE_MODEL = 'Qwen/Qwen3.6-27B'
EVALUATOR_MODEL = '88plug/Qwen3.6-27B-W8A16'
QUESTION_MAX_TOKENS = 2048
FINAL_REASONING_MAX_TOKENS = 4096
EVALUATOR_MAX_NUM_SEQS = 32
EVALUATOR_MAX_BATCHED_TOKENS = 16384
EVALUATOR_MAX_MODEL_LEN = 32768

def strip_thinking(text):
    ''' Remove Qwen thinking blocks so only stored conclusions leave the evaluator worker. '''
    if '</think>' in text:
        return text.rsplit('</think>', 1)[1].strip()

    if '<think>' in text:
        return ''

    return text.strip()

def evaluation_progress(*args, **kwargs):
    ''' Label vLLM request progress in interview-domain terms while keeping its token-rate statistics. '''
    kwargs['desc'] = 'Evaluating criteria'
    kwargs['unit'] = 'criterion'
    return tqdm(*args, **kwargs)

def build_prompt(tokenizer, system_prompt, context, thinking):
    ''' Apply the official Qwen3.6 chat template to one evaluator request. '''
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': context}
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=thinking)

def generate_text(llm, prompt, sampling_params):
    ''' Generate one evaluator response and remove hidden thinking from the stored result. '''
    output = llm.generate([prompt], sampling_params, use_tqdm=False)[0]
    return strip_thinking(output.outputs[0].text)

def run_evaluator_worker(job_description, transcript, questions, result_queue):
    ''' Evaluate every criterion as one vLLM batch, then produce the final constrained recruitment decision. '''
    llm = None
    answers = []
    result = ''
    error_message = ''

    try:
        from transformers import AutoTokenizer  # noqa: PLC0415
        from vllm import LLM, SamplingParams  # noqa: PLC0415
        from vllm.sampling_params import StructuredOutputsParams  # noqa: PLC0415

        tokenizer = AutoTokenizer.from_pretrained(EVALUATOR_BASE_MODEL)
        common_context = f'JOB DESCRIPTION\n{job_description}\n\nINTERVIEW TRANSCRIPT\n{transcript}\n\nCRITERION\n'
        question_prompts = [build_prompt(tokenizer, EVALUATOR_QUESTION_PROMPT, common_context + question, True) for question in questions]

        print('Loading Qwen3.6-27B W8A16 evaluator with vLLM TP=2...', flush=True)
        llm = LLM(model=EVALUATOR_MODEL, tokenizer=EVALUATOR_BASE_MODEL, tensor_parallel_size=2, dtype='bfloat16',
            language_model_only=True, gpu_memory_utilization=0.90, cpu_offload_gb=0, enable_prefix_caching=True,
            max_num_seqs=min(EVALUATOR_MAX_NUM_SEQS, max(1, len(questions))), max_num_batched_tokens=EVALUATOR_MAX_BATCHED_TOKENS,
            enable_chunked_prefill=True, max_model_len=EVALUATOR_MAX_MODEL_LEN, enforce_eager=False, performance_mode='throughput',
            distributed_executor_backend='mp', generation_config='vllm')

        question_sampling = SamplingParams(max_tokens=QUESTION_MAX_TOKENS, temperature=1.0, top_p=0.95, top_k=20,
            min_p=0.0, presence_penalty=0.0, repetition_penalty=1.0)
        outputs = llm.generate(question_prompts, question_sampling, use_tqdm=evaluation_progress)
        answers = [strip_thinking(output.outputs[0].text) for output in outputs]

        if len(answers) != len(questions) or any(not answer for answer in answers):
            error_message = 'Qwen3.6 returned an incomplete criterion batch.'

        if not error_message:
            assessments = '\n\n'.join(f'{index + 1}. {question}\nAssessment: {answers[index]}' for index, question in enumerate(questions))
            final_context = f'JOB DESCRIPTION\n{job_description}\n\nINTERVIEW TRANSCRIPT\n{transcript}\n\nCRITERION ASSESSMENTS\n{assessments}'
            reasoning_prompt = build_prompt(tokenizer, FINAL_CHOICE_PROMPT, final_context, True)
            reasoning_sampling = SamplingParams(max_tokens=FINAL_REASONING_MAX_TOKENS, temperature=1.0, top_p=0.95, top_k=20,
                min_p=0.0, presence_penalty=0.0, repetition_penalty=1.0)

            print('Generating final evaluation reasoning...', flush=True)
            decision_analysis = generate_text(llm, reasoning_prompt, reasoning_sampling)
            choice_context = f'{final_context}\n\nFINAL DECISION ANALYSIS\n{decision_analysis}'
            choice_prompt = build_prompt(tokenizer, FINAL_OUTPUT_PROMPT, choice_context, False)
            structured_output = StructuredOutputsParams(choice=['PROGRESS', 'NOT_PROGRESS'])
            choice_sampling = SamplingParams(max_tokens=8, temperature=0.0, structured_outputs=structured_output)
            result = generate_text(llm, choice_prompt, choice_sampling)

            if result not in ['PROGRESS', 'NOT_PROGRESS']:
                error_message = 'Qwen3.6 returned an invalid final evaluation decision.'

        if error_message:
            result_queue.put({'type': 'error', 'message': error_message})
        else:
            result_queue.put({'type': 'result', 'answers': answers, 'result': result})

    except Exception as error:  # noqa: BLE001
        traceback.print_exc()
        result_queue.put({'type': 'error', 'message': str(error)})

    finally:
        llm = None
        gc.collect()

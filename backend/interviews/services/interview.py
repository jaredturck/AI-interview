''' Apply interview policy around shared Qwen3.5-9B generation while persisting candidate and interviewer evidence. '''

from datetime import timedelta

from django.utils import timezone

from interviews.models import ConversationTurn
from interviews.services.content import INTERVIEWER_PROMPT
from interviews.services.runtime import model_runtime
from interviews.services.transcript import transcript_text, turn_list

INTERVIEW_MAX_MINUTES = 30
INTERVIEWER_MAX_TOKENS = 128
MAX_TEXT_CHARS = 12000
SAFE_FALLBACK = 'I can\'t help with that request. Let\'s return to the interview. Could you tell me more about your relevant experience?'

def build_system_prompt(interview, temporary_instruction=''):
    ''' Combine interviewer policy and the linked job snapshot with any temporary instruction needed for the current turn. '''
    parts = [INTERVIEWER_PROMPT, f'Job description:\n{interview.application.job.description}']

    if temporary_instruction:
        parts.append(temporary_instruction)

    return '\n\n'.join(parts)

def generate_interviewer_reply(interview, candidate_text='', temporary_instruction='', internal_user_message='', max_tokens=INTERVIEWER_MAX_TOKENS):
    ''' Generate one Qwen3.5-9B interviewer turn and block unsafe output before it reaches the candidate. '''
    system_prompt = build_system_prompt(interview, temporary_instruction)
    turns = turn_list(interview)

    if internal_user_message:
        turns.append({'role': 'user', 'text': internal_user_message})

    reply = model_runtime.suite.interviewer(system_prompt, turns, max_tokens=max_tokens).strip()

    if not reply:
        reply = 'Could you tell me a little more about your relevant experience?'

    response_safety = model_runtime.suite.guard_response(candidate_text, reply)
    return SAFE_FALLBACK if response_safety == 'Unsafe' else reply

def opening_message(interview):
    ''' Start the adaptive interview with a Qwen3.5-9B question grounded in the linked job description. '''
    instruction = 'Begin the interview with one relevant opening question based on the job description.'
    return generate_interviewer_reply(interview, internal_user_message=instruction)

def closing_message(interview):
    ''' End the candidate-facing conversation with a short Qwen3.5-9B closing before final evaluation. '''
    instruction = 'End the interview now with one brief, warm closing sentence.'
    return generate_interviewer_reply(interview, internal_user_message=instruction, max_tokens=24)

def rephrase_message(interview):
    ''' Support accessibility by asking the current interviewer question in a simpler, narrower form. '''
    instruction = 'Rephrase the last interviewer question so it is simpler, narrower and easier to understand. Ask one question.'
    return generate_interviewer_reply(interview, internal_user_message=instruction)

def interview_timed_out(interview):
    ''' Enforce the 30-minute interview limit across live and resumed sessions. '''
    if not interview.started_at:
        return False

    return timezone.now() >= interview.started_at + timedelta(minutes=INTERVIEW_MAX_MINUTES)

def finish_interview(interview, status='completed'):
    ''' Persist a terminal interview status and end time without overwriting an already-finished session. '''
    if interview.status in ['completed', 'terminated', 'evaluating', 'evaluated', 'evaluation_failed']:
        return

    interview.status = status
    interview.ended_at = timezone.now()
    interview.save(update_fields=['status', 'ended_at'])
    interview.application.status = 'evaluating'
    interview.application.save(update_fields=['status'])

def add_turn(interview, role, text):
    ''' Persist normalized candidate or interviewer text as evidence for later prompts and evaluation. '''
    return ConversationTurn.objects.create(interview=interview, role=role, text=text.strip())

def process_candidate_text(interview, text):
    ''' Apply timeout, safety, misuse and Qwen3.5-9B interviewer policy to one persisted candidate turn. '''
    text = text.strip()[:MAX_TEXT_CHARS]

    if not text:
        return {'reply': '', 'finished': False}

    add_turn(interview, 'user', text)

    if interview_timed_out(interview):
        reply = closing_message(interview)
        add_turn(interview, 'assistant', reply)
        finish_interview(interview)
        return {'reply': reply, 'finished': True}

    safety = model_runtime.suite.guard_user(text)
    misuse = model_runtime.suite.misuse(transcript_text(interview))

    if misuse == 'TERMINATE':
        reply = closing_message(interview)
        add_turn(interview, 'assistant', reply)
        finish_interview(interview, status='terminated')
        return {'reply': reply, 'finished': True}

    instruction = ''

    if misuse == 'REDIRECT':
        instruction = 'Briefly steer the conversation back to the interview with one relevant question.'

    if safety == 'Unsafe':
        instruction = ('The candidate\'s latest request is unsafe. Give a brief refusal and immediately return to the interview '
            'with one short job-relevant question.')

    reply = generate_interviewer_reply(interview, text, instruction)
    add_turn(interview, 'assistant', reply)
    return {'reply': reply, 'finished': False}

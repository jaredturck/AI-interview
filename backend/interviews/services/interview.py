''' Conduct the live interview and persist its text turns. '''

from datetime import timedelta

from django.utils import timezone

from interviews.models import ConversationTurn
from interviews.services.content import INTERVIEWER_PROMPT, get_job_description
from interviews.services.runtime import model_runtime
from interviews.services.transcript import transcript_text, turn_list

INTERVIEW_MAX_MINUTES = 30
MAX_TEXT_CHARS = 12000
SAFE_FALLBACK = 'I can\'t help with that request. Let\'s return to the interview. Could you tell me about the technical work you\'ve done?'

def build_system_prompt(temporary_instruction=''):
    ''' Build the live interviewer context for the current candidate turn. '''
    parts = [INTERVIEWER_PROMPT, f'Job description:\n{get_job_description()}']

    if temporary_instruction:
        parts.append(temporary_instruction)

    return '\n\n'.join(parts)

def generate_interviewer_reply(interview, candidate_text='', temporary_instruction='', max_tokens=32):
    ''' Generate and safety-check one short interviewer response. '''
    system_prompt = build_system_prompt(temporary_instruction)
    reply = model_runtime.suite.interviewer(system_prompt, turn_list(interview), max_tokens=max_tokens).strip()

    if not reply:
        reply = 'Could you tell me a little more about your experience?'

    response_safety = model_runtime.suite.guard_response(candidate_text, reply)
    return SAFE_FALLBACK if response_safety == 'Unsafe' else reply

def opening_message(interview):
    ''' Generate the opening interview question. '''
    return generate_interviewer_reply(interview)

def closing_message(interview):
    ''' Generate a brief friendly interview closing. '''
    instruction = 'End the interview now with one brief, warm closing sentence.'
    return generate_interviewer_reply(interview, temporary_instruction=instruction, max_tokens=24)

def rephrase_message(interview):
    ''' Rephrase the latest question with greater specificity and simplicity. '''
    instruction = 'Rephrase the last interviewer question so it is simpler, narrower and easier to understand. Ask one question.'
    return generate_interviewer_reply(interview, temporary_instruction=instruction, max_tokens=32)

def interview_timed_out(interview):
    ''' Return whether the interview time limit has elapsed. '''
    if not interview.started_at:
        return False

    return timezone.now() >= interview.started_at + timedelta(minutes=INTERVIEW_MAX_MINUTES)

def finish_interview(interview, status='completed'):
    ''' Mark an active interview as finished. '''
    if interview.status in ['completed', 'terminated', 'evaluating', 'evaluated', 'evaluation_failed']:
        return

    interview.status = status
    interview.ended_at = timezone.now()
    interview.save(update_fields=['status', 'ended_at'])

def add_turn(interview, role, text):
    ''' Append one normalized text turn to the interview transcript. '''
    return ConversationTurn.objects.create(interview=interview, role=role, text=text.strip())

def process_candidate_text(interview, text):
    ''' Process one candidate turn through safety, misuse and interviewer models. '''
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
        instruction = 'Briefly steer the conversation back to the technical interview with one relevant question.'

    if safety == 'Unsafe':
        instruction = ('The candidate\'s latest request is unsafe. Give a brief refusal and immediately return to the technical interview '
            'with one short question.')

    reply = generate_interviewer_reply(interview, text, instruction)
    add_turn(interview, 'assistant', reply)
    return {'reply': reply, 'finished': False}

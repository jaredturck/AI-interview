''' Apply interview policy around shared Qwen3.5-9B generation while persisting candidate and interviewer evidence. '''

from datetime import timedelta

from django.utils import timezone

from interviews.models import ConversationTurn
from interviews.services.content import INTERVIEWER_PROMPT
from interviews.services.runtime import model_runtime
from interviews.services.transcript import transcript_text, turn_list

INTERVIEW_MAX_MINUTES = 15
INTERVIEW_WRAP_UP_MINUTES = 13
INTERVIEWER_MAX_TOKENS = 128
MAX_TEXT_CHARS = 12000
SAFE_FALLBACK = 'I can\'t help with that request. Let\'s return to the interview. Could you tell me more about your relevant experience?'

def interview_elapsed_seconds(interview):
    ''' Return elapsed interview time from the persisted server-side start timestamp. '''
    if not interview.started_at:
        return 0

    return max(0, int((timezone.now() - interview.started_at).total_seconds()))

def interview_remaining_seconds(interview):
    ''' Return seconds remaining before the application-enforced hard interview deadline. '''
    if not interview.started_at:
        return INTERVIEW_MAX_MINUTES * 60

    return max(0, INTERVIEW_MAX_MINUTES * 60 - interview_elapsed_seconds(interview))

def interview_should_wrap_up(interview):
    ''' Force the final interview phase once the soft wrap-up threshold has been reached. '''
    return bool(interview.started_at and interview_elapsed_seconds(interview) >= INTERVIEW_WRAP_UP_MINUTES * 60)

def format_duration(seconds):
    ''' Format prompt-only elapsed and remaining durations without exposing clock implementation details. '''
    minutes, remainder = divmod(max(0, int(seconds)), 60)
    return f'{minutes} minutes {remainder} seconds'

def build_system_prompt(interview, temporary_instruction=''):
    ''' Combine interviewer policy, hidden recruitment specification and current timing state for the linked Job. '''
    job = interview.application.job
    none_configured = 'None configured.'
    elapsed_seconds = interview_elapsed_seconds(interview)
    remaining_seconds = interview_remaining_seconds(interview)
    parts = [
        INTERVIEWER_PROMPT,
        f'JOB DESCRIPTION\n{job.description}',
        f'ESSENTIAL REQUIREMENTS\n{job.essential_requirements or none_configured}',
        f'REQUIREMENTS REQUIRING EXTERNAL VERIFICATION\n{job.verification_requirements or none_configured}',
        f'EVALUATION CRITERIA\n{job.evaluation_questions}',
        (f'INTERVIEW STATE\nPhase: {interview.phase.upper()}\nMaximum duration: {INTERVIEW_MAX_MINUTES} minutes.\n'
            f'Elapsed time: {format_duration(elapsed_seconds)}.\nRemaining time before hard stop: {format_duration(remaining_seconds)}.'),
    ]

    if temporary_instruction:
        parts.append(temporary_instruction)

    return '\n\n'.join(parts)

def generate_interviewer_reply(interview, candidate_text='', temporary_instruction='', internal_user_message='', max_tokens=INTERVIEWER_MAX_TOKENS):
    ''' Generate one Qwen3.5-9B interviewer turn and block unsafe output before it reaches the candidate. '''
    system_prompt = build_system_prompt(interview, temporary_instruction)
    turns = turn_list(interview)

    if internal_user_message and turns and turns[-1]['role'] == 'user':
        system_prompt = f'{system_prompt}\n\nCURRENT CONTROL INSTRUCTION\n{internal_user_message}'
    elif internal_user_message:
        turns.append({'role': 'user', 'text': internal_user_message})

    reply = model_runtime.suite.interviewer(system_prompt, turns, max_tokens=max_tokens).strip()

    if not reply:
        reply = 'Could you tell me a little more about your relevant experience?'

    response_safety = model_runtime.suite.guard_response(candidate_text, reply)
    return SAFE_FALLBACK if response_safety == 'Unsafe' else reply

def opening_message(interview):
    ''' Start the adaptive interview with a question grounded in the linked recruitment specification. '''
    instruction = 'Begin the interview with one relevant opening question. Start gathering evidence for the most important role requirements.'
    return generate_interviewer_reply(interview, internal_user_message=instruction)

def closing_message(interview):
    ''' End the candidate-facing conversation neutrally without predicting or implying the recruitment outcome. '''
    instruction = ('End the interview now with one brief, warm closing. State that the interview is complete and the responses will now be evaluated. '
        'Do not praise, score, predict or imply whether the candidate will progress.')
    return generate_interviewer_reply(interview, internal_user_message=instruction, max_tokens=40)

def rephrase_message(interview):
    ''' Support accessibility by asking the current interviewer question in a simpler, narrower form. '''
    instruction = 'Rephrase the last interviewer question so it is simpler, narrower and easier to understand. Ask one question.'
    return generate_interviewer_reply(interview, internal_user_message=instruction)

def interview_timed_out(interview):
    ''' Enforce the 15-minute interview limit across live and resumed sessions. '''
    if not interview.started_at:
        return False

    return timezone.now() >= interview.started_at + timedelta(minutes=INTERVIEW_MAX_MINUTES)

def set_interview_phase(interview, phase):
    ''' Persist lifecycle phase changes so reconnects cannot restart a nearly completed interview. '''
    if interview.phase == phase:
        return

    interview.phase = phase
    interview.save(update_fields=['phase'])

def interview_state_decision(interview):
    ''' Ask the shared model for a constrained evidence-coverage decision without letting it score the candidate. '''
    job = interview.application.job
    decision = model_runtime.suite.interview_state(job.description, job.essential_requirements, job.verification_requirements,
        job.evaluation_questions, transcript_text(interview), interview.phase, interview_elapsed_seconds(interview), interview_remaining_seconds(interview))
    return decision if decision in ['CONTINUE', 'WRAP_UP', 'END'] else 'CONTINUE'

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

def finish_with_generated_closing(interview, status='completed'):
    ''' Persist one neutral closing turn and terminate interview policy processing. '''
    reply = closing_message(interview)
    add_turn(interview, 'assistant', reply)
    finish_interview(interview, status=status)
    return {'reply': reply, 'finished': True}

def process_candidate_text(interview, text):
    ''' Apply timing, safety, misuse, stopping and interviewer policy to one persisted candidate turn. '''
    text = text.strip()[:MAX_TEXT_CHARS]

    if not text:
        return {'reply': '', 'finished': False}

    add_turn(interview, 'user', text)

    if interview_timed_out(interview):
        return finish_with_generated_closing(interview)

    safety = model_runtime.suite.guard_user(text)
    misuse = model_runtime.suite.misuse(transcript_text(interview))

    if misuse == 'TERMINATE':
        return finish_with_generated_closing(interview, status='terminated')

    if interview.phase == 'wrap_up':
        return finish_with_generated_closing(interview)

    instruction_parts = []

    if misuse == 'REDIRECT':
        instruction_parts.append('Briefly steer the conversation back to the interview with one relevant question.')

    if safety == 'Unsafe':
        instruction_parts.append('The candidate\'s latest request is unsafe. Give a brief refusal and immediately return to the interview '
            'with one short job-relevant question.')

    if interview_should_wrap_up(interview):
        decision = 'WRAP_UP'
    elif misuse == 'CONTINUE' and safety != 'Unsafe':
        decision = interview_state_decision(interview)
    else:
        decision = 'CONTINUE'

    if decision == 'END':
        return finish_with_generated_closing(interview)

    if decision == 'WRAP_UP':
        set_interview_phase(interview, 'wrap_up')
        instruction_parts.append('The interview is now in WRAP_UP. Ask at most one brief final high-value question. '
            'Choose the most important remaining evidence gap if one exists; otherwise invite one brief final comment. '
            'Do not introduce a substantial new topic.')

    reply = generate_interviewer_reply(interview, text, '\n\n'.join(instruction_parts))
    add_turn(interview, 'assistant', reply)
    return {'reply': reply, 'finished': False}

''' Run Qwen3.6 post-interview criterion assessment and binary stage-two progression decisions. '''

import logging, threading

from django.db import close_old_connections

from interviews.models import EvaluationAnswer, InterviewSession
from interviews.services.content import get_evaluation_questions, get_job_description
from interviews.services.runtime import model_runtime
from interviews.services.transcript import transcript_text

LOGGER = logging.getLogger(__name__)

def evaluate_interview(interview_id):
    ''' Run the complete Qwen3.6 evaluation pipeline and persist criterion evidence plus the binary progression outcome. '''
    close_old_connections()
    interview = InterviewSession.objects.get(id=interview_id)

    if not model_runtime.begin_evaluation(interview.id):
        interview.status = 'evaluation_failed'
        interview.save(update_fields=['status'])
        close_old_connections()
        return False

    completed = False

    try:
        interview.status = 'evaluating'
        interview.save(update_fields=['status'])
        transcript = transcript_text(interview)
        job_description = get_job_description()
        questions = get_evaluation_questions()
        answers = []
        EvaluationAnswer.objects.filter(interview=interview).delete()

        if not questions:
            return False

        for index, question in enumerate(questions):
            answer = model_runtime.suite.evaluate_question(job_description, transcript, question).strip()

            if not answer:
                return False

            EvaluationAnswer.objects.create(interview=interview, question_index=index, question=question, answer=answer)
            answers.append({'question': question, 'answer': answer})

        result = model_runtime.suite.final_choice(job_description, transcript, answers)

        if result not in ['PROGRESS', 'NOT_PROGRESS']:
            return False

        interview.result = result
        interview.status = 'evaluated'
        interview.save(update_fields=['result', 'status'])
        completed = True
        return True

    finally:
        if not completed:
            InterviewSession.objects.filter(id=interview.id).update(status='evaluation_failed')

        model_runtime.finish_evaluation()
        close_old_connections()

def run_evaluation(interview_id):
    ''' Protect the background evaluation boundary so unexpected failures become explicit evaluation_failed state. '''
    try:
        evaluate_interview(interview_id)

    except Exception as error:  # noqa: BLE001
        LOGGER.exception('Interview evaluation failed: %s', error)
        InterviewSession.objects.filter(id=interview_id).update(status='evaluation_failed')
        model_runtime.release_interview(interview_id)
        close_old_connections()

def start_evaluation(interview_id):
    ''' Move final evaluation off WebSocket handling so interview completion can return immediately. '''
    thread = threading.Thread(target=run_evaluation, args=(str(interview_id),), daemon=True)
    thread.start()
    return thread

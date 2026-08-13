''' Run Qwen3.6 post-interview criterion assessment and binary stage-two progression decisions. '''

import logging, threading

from django.db import close_old_connections

from interviews.models import EvaluationAnswer, InterviewSession
from interviews.services.runtime import model_runtime
from interviews.services.transcript import transcript_text

LOGGER = logging.getLogger(__name__)

def mark_application_complete(interview_id):
    ''' Keep application workflow state aligned with a terminal automated evaluation state. '''
    interview = InterviewSession.objects.select_related('application').get(id=interview_id)
    interview.application.status = 'complete'
    interview.application.save(update_fields=['status'])

def evaluate_interview(interview_id):
    ''' Run the complete Qwen3.6 evaluation pipeline and persist criterion evidence plus the binary progression outcome. '''
    close_old_connections()
    interview = InterviewSession.objects.select_related('application__job').get(id=interview_id)

    if not model_runtime.begin_evaluation(interview.id):
        interview.status = 'evaluation_failed'
        interview.save(update_fields=['status'])
        mark_application_complete(interview.id)
        close_old_connections()
        return False

    completed = False

    try:
        interview.status = 'evaluating'
        interview.save(update_fields=['status'])
        interview.application.status = 'evaluating'
        interview.application.save(update_fields=['status'])
        transcript = transcript_text(interview)
        job_description = interview.application.job.description
        questions = interview.application.job.evaluation_question_list()
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
        interview.application.status = 'complete'
        interview.application.save(update_fields=['status'])
        completed = True
        return True

    finally:
        if not completed:
            InterviewSession.objects.filter(id=interview.id).update(status='evaluation_failed')
            mark_application_complete(interview.id)

        model_runtime.finish_evaluation()
        close_old_connections()

def run_evaluation(interview_id):
    ''' Protect the background evaluation boundary so unexpected failures become explicit evaluation_failed state. '''
    try:
        evaluate_interview(interview_id)

    except Exception as error:  # noqa: BLE001
        LOGGER.exception('Interview evaluation failed: %s', error)
        interview = InterviewSession.objects.filter(id=interview_id).first()

        if not interview or interview.status != 'evaluated':
            InterviewSession.objects.filter(id=interview_id).update(status='evaluation_failed')
            mark_application_complete(interview_id)

        model_runtime.release_interview(interview_id)
        close_old_connections()

def start_evaluation(interview_id):
    ''' Move final evaluation off WebSocket handling so interview completion can return immediately. '''
    thread = threading.Thread(target=run_evaluation, args=(str(interview_id),), daemon=True)
    thread.start()
    return thread

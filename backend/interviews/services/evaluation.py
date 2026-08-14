''' Run Qwen3.6 post-interview criterion assessment and binary stage-two progression decisions. '''

import logging, threading

from django.db import close_old_connections
from tqdm import tqdm

from interviews.models import EvaluationAnswer, InterviewSession, JobApplication
from interviews.services.runtime import model_runtime
from interviews.services.transcript import transcript_text

LOGGER = logging.getLogger(__name__)

def mark_application_complete(interview_id):
    ''' Keep application workflow state aligned when the candidate has not deleted the interview during evaluation. '''
    JobApplication.objects.filter(interview__id=interview_id).update(status='complete')

def evaluate_interview(interview_id):
    ''' Run the complete Qwen3.6 evaluation pipeline and persist criterion evidence plus the binary progression outcome. '''
    close_old_connections()
    interview = InterviewSession.objects.select_related('application__job').get(id=interview_id)

    if not model_runtime.begin_evaluation(interview.id):
        InterviewSession.objects.filter(id=interview.id).update(status='evaluation_failed')
        mark_application_complete(interview.id)
        close_old_connections()
        return False

    completed = False

    try:
        InterviewSession.objects.filter(id=interview.id).update(status='evaluating')
        JobApplication.objects.filter(id=interview.application_id).update(status='evaluating')
        transcript = transcript_text(interview)
        job_description = interview.application.job.description
        questions = interview.application.job.evaluation_question_list()
        answers = []
        EvaluationAnswer.objects.filter(interview=interview).delete()

        if not questions:
            return False

        with tqdm(total=len(questions), desc='Evaluating criteria', unit='criterion') as progress:
            for index, question in enumerate(questions):
                progress.set_postfix_str(f'{index + 1}/{len(questions)}')
                answer = model_runtime.suite.evaluate_question(job_description, transcript, question).strip()

                if not answer:
                    return False

                EvaluationAnswer.objects.create(interview=interview, question_index=index, question=question, answer=answer)
                answers.append({'question': question, 'answer': answer})
                progress.update()

        print('Generating final evaluation decision...', flush=True)
        result = model_runtime.suite.final_choice(job_description, transcript, answers)

        if result not in ['PROGRESS', 'NOT_PROGRESS']:
            return False

        updated = InterviewSession.objects.filter(id=interview.id).update(result=result, status='evaluated')

        if not updated:
            return False

        JobApplication.objects.filter(id=interview.application_id).update(status='complete')
        completed = True
        return True

    finally:
        try:
            if not completed:
                InterviewSession.objects.filter(id=interview.id).update(status='evaluation_failed')
                mark_application_complete(interview.id)

        finally:
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

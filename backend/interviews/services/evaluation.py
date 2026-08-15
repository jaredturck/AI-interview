''' Run structured Qwen3.5-9B evidence assessment and binary stage-two progression decisions. '''

import logging, threading

from django.db import close_old_connections

from interviews.models import EvaluationAnswer, InterviewSession, JobApplication
from interviews.services.runtime import model_runtime
from interviews.services.transcript import transcript_text

LOGGER = logging.getLogger(__name__)
ESSENTIAL_ASSESSMENTS = ['MET', 'PARTIALLY_MET', 'NOT_MET', 'INSUFFICIENT_EVIDENCE', 'CONTRADICTORY_EVIDENCE']
EVALUATION_ASSESSMENTS = ['POSITIVE', 'MIXED', 'NEGATIVE', 'INSUFFICIENT_EVIDENCE', 'CONTRADICTORY_EVIDENCE']
VERIFICATION_ASSESSMENTS = ['CLAIMED', 'NOT_CLAIMED', 'UNCLEAR']

def mark_application_complete(interview_id):
    ''' Keep application workflow state aligned when the candidate has not deleted the interview during evaluation. '''
    JobApplication.objects.filter(interview__id=interview_id).update(status='complete')

def build_criteria(job):
    ''' Flatten the immutable Job specification into one ordered criterion stream for evaluation persistence. '''
    criteria = []

    for criterion_type, questions in [
        ('essential', job.essential_requirement_list()),
        ('verification', job.verification_requirement_list()),
        ('evaluation', job.evaluation_question_list()),
    ]:
        for question in questions:
            criteria.append({'question_index': len(criteria), 'criterion_type': criterion_type, 'question': question})

    return criteria

def assessment_valid(item):
    ''' Accept only criterion-type labels that the constrained evaluator contract permits. '''
    criterion_type = item.get('criterion_type')
    assessment = item.get('assessment')

    if criterion_type == 'verification':
        return assessment in VERIFICATION_ASSESSMENTS

    if criterion_type == 'essential':
        return assessment in ESSENTIAL_ASSESSMENTS

    if criterion_type == 'evaluation':
        return assessment in EVALUATION_ASSESSMENTS

    return False

def hard_gate_result(assessments):
    ''' Return NOT_PROGRESS when a mandatory interview or verification gate is not positively satisfied. '''
    for item in assessments:
        if item['criterion_type'] == 'essential' and item['assessment'] != 'MET':
            return 'NOT_PROGRESS'

        if item['criterion_type'] == 'verification' and item['assessment'] != 'CLAIMED':
            return 'NOT_PROGRESS'

    return ''

def evaluate_interview(interview_id):
    ''' Run criterion assessment, enforce mandatory gates and persist the final first-stage outcome. '''
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
        job = interview.application.job
        criteria = build_criteria(job)
        EvaluationAnswer.objects.filter(interview=interview).delete()

        if not criteria:
            return False

        print(f'Evaluation started: {len(criteria)} criteria.', flush=True)
        evaluation = model_runtime.suite.evaluate_criteria(job.description, transcript, criteria)
        assessments = evaluation.get('assessments') or []
        error = evaluation.get('error') or ''

        if error:
            LOGGER.error('Evaluator failed: %s', error)
            return False

        if len(assessments) != len(criteria):
            return False

        for index, item in enumerate(assessments):
            criterion = criteria[index]

            if item.get('question_index') != criterion['question_index'] or item.get('criterion_type') != criterion['criterion_type']:
                return False

            question_matches = item.get('question') == criterion['question']
            answer_present = bool(str(item.get('answer') or '').strip())

            if not question_matches or not answer_present or not assessment_valid(item):
                return False

        result = hard_gate_result(assessments)

        if not result:
            final = model_runtime.suite.final_evaluation(job.description, transcript, assessments)
            result = final.get('result') or ''
            error = final.get('error') or ''

            if error:
                LOGGER.error('Final evaluator failed: %s', error)
                return False

        if result not in ['PROGRESS', 'NOT_PROGRESS']:
            return False

        evaluation_answers = []

        for item in assessments:
            evaluation_answers.append(EvaluationAnswer(
                interview=interview,
                question_index=item['question_index'],
                criterion_type=item['criterion_type'],
                question=item['question'],
                assessment=item['assessment'],
                answer=item['answer'].strip(),
            ))

        EvaluationAnswer.objects.bulk_create(evaluation_answers)
        updated = InterviewSession.objects.filter(id=interview.id).update(result=result, status='evaluated')

        if not updated:
            return False

        JobApplication.objects.filter(id=interview.application_id).update(status='complete')
        print(f'Evaluation completed: {result}.', flush=True)
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

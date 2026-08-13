import threading

from django.db import close_old_connections

from interviews.models import EvaluationAnswer, InterviewSession
from interviews.services.runtime import model_runtime
from interviews.services.transcript import transcript_text


def evaluate_interview(interview_id):
    close_old_connections()
    interview = InterviewSession.objects.select_related("job").get(id=interview_id)

    try:
        started = model_runtime.begin_evaluation(interview.id)
    except Exception:
        InterviewSession.objects.filter(id=interview.id).update(status="evaluation_failed")
        close_old_connections()
        return False

    if not started:
        InterviewSession.objects.filter(id=interview.id).update(status="evaluation_failed")
        close_old_connections()
        return False

    interview.status = "evaluating"
    interview.save(update_fields=["status"])
    completed = False

    try:
        transcript = transcript_text(interview)
        job_description = interview.job.description
        answers = []

        EvaluationAnswer.objects.filter(interview=interview).delete()

        if not interview.job.evaluation_questions:
            return False

        for index, question in enumerate(interview.job.evaluation_questions):
            answer = model_runtime.suite.evaluate_question(job_description, transcript, question)
            if not answer.strip():
                return False
            EvaluationAnswer.objects.create(
                interview=interview,
                question_index=index,
                question=question,
                answer=answer,
            )
            answers.append({"question": question, "answer": answer})

        synthesis = model_runtime.suite.synthesize(job_description, transcript, answers)
        if not synthesis.strip():
            return False

        result = model_runtime.suite.final_choice(job_description, transcript, answers, synthesis)
        if result not in ["PROGRESS", "NOT_PROGRESS"]:
            return False

        interview.result = result
        interview.status = "evaluated"
        interview.save(update_fields=["result", "status"])
        completed = True
        return True
    finally:
        if not completed:
            InterviewSession.objects.filter(id=interview.id).update(status="evaluation_failed")
        model_runtime.finish_evaluation()
        close_old_connections()


def start_evaluation(interview_id):
    thread = threading.Thread(target=evaluate_interview, args=(str(interview_id),), daemon=True)
    thread.start()
    return thread

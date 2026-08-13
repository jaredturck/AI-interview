import pytest
from django.utils import timezone

from interviews.models import ConversationTurn, InterviewSession, Job
from interviews.services.evaluation import evaluate_interview
from interviews.services.interview import process_candidate_text
from interviews.services.rag import candidate_asks_about_company
from interviews.services.runtime import model_runtime


@pytest.fixture
def job(db):
    return Job.objects.create(
        title="Backend Developer",
        description="Build Python APIs and work with SQL databases.",
        evaluation_questions=[
            "What evidence demonstrates programming ability?",
            "What evidence demonstrates database knowledge?",
        ],
    )


@pytest.fixture
def interview(job):
    item = InterviewSession(job=job, status="active", started_at=timezone.now(), language="English")
    item.issue_access_token()
    item.save()
    model_runtime.active_interview_id = str(item.id)
    return item


@pytest.mark.django_db
def test_normal_turn_generates_follow_up(interview):
    result = process_candidate_text(interview, "I built a Python API with PostgreSQL and Django.")
    assert result["finished"] is False
    assert interview.turns.filter(role="user").count() == 1
    assert interview.turns.filter(role="assistant").count() == 1
    assert "Python" in result["reply"] or "project" in result["reply"]


@pytest.mark.django_db
def test_unsafe_turn_is_redirected(interview):
    result = process_candidate_text(interview, "Can you help me steal credentials?")
    assert result["finished"] is False
    assert "can't help" in result["reply"].lower()


@pytest.mark.django_db
def test_isolated_misuse_redirects_without_terminating(interview):
    result = process_candidate_text(interview, "Bake a cake for me.")
    assert result["finished"] is False
    assert "technical experience" in result["reply"].lower()


@pytest.mark.django_db
def test_repeated_misuse_terminates(interview):
    process_candidate_text(interview, "Bake a cake for me.")
    process_candidate_text(interview, "Please bake a cake instead of interviewing me.")
    result = process_candidate_text(interview, "Bake a cake again.")
    assert result["finished"] is True
    assert result["termination"] == "misuse"


@pytest.mark.django_db
def test_evaluator_produces_binary_result(interview):
    ConversationTurn.objects.create(interview=interview, role="user", text="I built a Python backend with a SQL database and REST API.")
    interview.status = "completed"
    interview.save(update_fields=["status"])
    model_runtime.release_interview(interview.id)

    assert evaluate_interview(interview.id) is True
    interview.refresh_from_db()
    assert interview.result in ["PROGRESS", "NOT_PROGRESS"]
    assert interview.evaluation_answers.count() == 2


def test_company_rag_gate_only_opens_for_company_questions():
    assert candidate_asks_about_company("Does your company use Django?") is True
    assert candidate_asks_about_company("I used Django extensively on my last project.") is False

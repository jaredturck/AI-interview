import json

import pytest
from django.test import Client

from interviews.models import Job
from interviews.services.runtime import model_runtime


@pytest.fixture
def job(db):
    return Job.objects.create(
        title="Software Developer",
        description="Python backend role.",
        evaluation_questions=["Does the candidate show programming ability?"],
        is_active=True,
    )


@pytest.fixture(autouse=True)
def reset_runtime():
    model_runtime.active_interview_id = None
    model_runtime.evaluating = False
    model_runtime.connections = {}
    yield
    model_runtime.active_interview_id = None
    model_runtime.evaluating = False
    model_runtime.connections = {}


@pytest.mark.django_db
def test_start_and_status(job):
    client = Client()
    response = client.post(
        "/api/interviews/start/",
        data=json.dumps({"job_id": job.id, "language": "English"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.json()

    status = client.get(
        f"/api/interviews/{data['interview_id']}/status/",
        HTTP_X_INTERVIEW_TOKEN=data["access_token"],
    )
    assert status.status_code == 200
    assert status.json()["status"] == "created"


@pytest.mark.django_db
def test_review_request_requires_session_token(job):
    client = Client()
    response = client.post(
        "/api/interviews/start/",
        data=json.dumps({"job_id": job.id, "language": "English"}),
        content_type="application/json",
    )
    data = response.json()

    review = client.post(
        f"/api/interviews/{data['interview_id']}/review/",
        data=json.dumps({"name": "Candidate", "email": "candidate@example.com", "explanation": "The microphone failed."}),
        content_type="application/json",
        HTTP_X_INTERVIEW_TOKEN=data["access_token"],
    )
    assert review.status_code == 201

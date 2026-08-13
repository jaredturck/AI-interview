''' HTTP endpoint tests. '''

import json

import pytest
from django.test import Client

from interviews.models import InterviewSession
from interviews.services.runtime import model_runtime

@pytest.fixture(autouse=True)
def reset_runtime():
    ''' Reset process-wide mock worker ownership around each test. '''
    model_runtime.active_interview_id = None
    model_runtime.evaluating = False
    model_runtime.connections = {}
    yield
    model_runtime.active_interview_id = None
    model_runtime.evaluating = False
    model_runtime.connections = {}

@pytest.mark.django_db
def test_start_and_status():
    ''' Start an interview directly from file-backed role configuration. '''
    client = Client()
    response = client.post('/api/interviews/start/', data=json.dumps({'language': 'English'}), content_type='application/json')
    assert response.status_code == 201
    data = response.json()

    status = client.get(f'/api/interviews/{data["interview_id"]}/status/', HTTP_X_INTERVIEW_TOKEN=data['access_token'])
    assert status.status_code == 200
    assert status.json()['status'] == 'created'

@pytest.mark.django_db
def test_review_request_after_evaluation():
    ''' Accept a candidate review request with the matching session token. '''
    client = Client()
    response = client.post('/api/interviews/start/', data=json.dumps({'language': 'English'}), content_type='application/json')
    data = response.json()
    InterviewSession.objects.filter(id=data['interview_id']).update(status='evaluated', result='NOT_PROGRESS')
    review_data = {'name': 'Candidate', 'email': 'candidate@example.com', 'explanation': 'The microphone failed.'}
    review = client.post(f'/api/interviews/{data["interview_id"]}/review/', data=json.dumps(review_data), content_type='application/json',
        HTTP_X_INTERVIEW_TOKEN=data['access_token'])
    assert review.status_code == 201

@pytest.mark.django_db
def test_review_request_waits_for_automated_processing():
    ''' Require the automated process to finish before human review can be requested. '''
    client = Client()
    response = client.post('/api/interviews/start/', data=json.dumps({'language': 'English'}), content_type='application/json')
    data = response.json()
    review_data = {'name': 'Candidate', 'email': 'candidate@example.com', 'explanation': 'I would like the interview reviewed.'}
    review = client.post(f'/api/interviews/{data["interview_id"]}/review/', data=json.dumps(review_data), content_type='application/json',
        HTTP_X_INTERVIEW_TOKEN=data['access_token'])
    assert review.status_code == 409

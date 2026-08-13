''' HTTP endpoint tests. '''

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from interviews.models import InterviewSession

User = get_user_model()

def create_user(email='candidate@example.com', password='A-strong-test-password-42'):
    ''' Create one candidate test account. '''
    return User.objects.create_user(username=email, email=email, password=password)

@pytest.mark.django_db
def test_signup_creates_authenticated_candidate():
    ''' Create a candidate account and authenticated session. '''
    client = Client()
    response = client.post('/api/auth/signup/', data=json.dumps({'email': 'candidate@example.com', 'password': 'A-strong-test-password-42'}),
        content_type='application/json')
    assert response.status_code == 201
    assert response.json()['authenticated'] is True
    assert User.objects.filter(username='candidate@example.com').exists()

@pytest.mark.django_db
def test_interview_requires_authentication():
    ''' Prevent anonymous candidates from starting interviews. '''
    client = Client()
    response = client.post('/api/interviews/start/', data='{}', content_type='application/json')
    assert response.status_code == 401

@pytest.mark.django_db
def test_start_and_status_are_owned_by_account():
    ''' Start an interview and keep its status private to its owner. '''
    owner = create_user()
    other = create_user('other@example.com')
    client = Client()
    client.force_login(owner)
    response = client.post('/api/interviews/start/', data=json.dumps({'confirm_transcript': True}), content_type='application/json')
    assert response.status_code == 201
    interview_id = response.json()['interview_id']

    status = client.get(f'/api/interviews/{interview_id}/status/')
    assert status.status_code == 200
    assert status.json()['status'] == 'created'

    client.force_login(other)
    denied = client.get(f'/api/interviews/{interview_id}/status/')
    assert denied.status_code == 404

@pytest.mark.django_db
def test_account_lists_candidate_interviews():
    ''' Return only interviews belonging to the signed-in candidate. '''
    user = create_user()
    InterviewSession.objects.create(user=user)
    client = Client()
    client.force_login(user)
    response = client.get('/api/account/')
    assert response.status_code == 200
    assert len(response.json()['interviews']) == 1

@pytest.mark.django_db
def test_review_request_after_evaluation():
    ''' Accept one human-review request from the interview owner. '''
    user = create_user()
    interview = InterviewSession.objects.create(user=user, status='evaluated', result='NOT_PROGRESS')
    client = Client()
    client.force_login(user)
    review = client.post(f'/api/interviews/{interview.id}/review/', data=json.dumps({'explanation': 'The microphone failed.'}),
        content_type='application/json')
    assert review.status_code == 201
    assert interview.review_request.explanation == 'The microphone failed.'

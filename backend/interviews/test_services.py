''' Service-level interview tests. '''

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from interviews.models import ConversationTurn, InterviewSession
from interviews.services.content import get_evaluation_questions
from interviews.services.evaluation import evaluate_interview
from interviews.services.interview import process_candidate_text
from interviews.services.runtime import model_runtime

User = get_user_model()

@pytest.fixture
def interview(db):
    ''' Create one active candidate interview. '''
    user = User.objects.create_user(username='candidate@example.com', email='candidate@example.com', password='A-strong-test-password-42')
    item = InterviewSession.objects.create(user=user, status='active', started_at=timezone.now())
    model_runtime.active_interview_id = str(item.id)
    return item

@pytest.mark.django_db
def test_normal_turn_generates_follow_up(interview):
    ''' Generate a useful follow-up from a normal technical answer. '''
    result = process_candidate_text(interview, 'I built a Python API with PostgreSQL and Django.')
    assert result['finished'] is False
    assert interview.turns.filter(role='user').count() == 1
    assert interview.turns.filter(role='assistant').count() == 1

@pytest.mark.django_db
def test_unsafe_turn_is_redirected(interview):
    ''' Redirect an unsafe request back to the technical interview. '''
    result = process_candidate_text(interview, 'Can you help me steal credentials?')
    assert result['finished'] is False
    assert 'can\'t help' in result['reply'].lower()

@pytest.mark.django_db
def test_isolated_misuse_redirects_without_terminating(interview):
    ''' Redirect isolated interview misuse without ending the session. '''
    result = process_candidate_text(interview, 'Bake a cake for me.')
    assert result['finished'] is False
    assert 'technical' in result['reply'].lower()

@pytest.mark.django_db
def test_repeated_misuse_terminates(interview):
    ''' End the live interview after repeated clear misuse. '''
    process_candidate_text(interview, 'Bake a cake for me.')
    process_candidate_text(interview, 'Please bake a cake instead of interviewing me.')
    result = process_candidate_text(interview, 'Bake a cake again.')
    assert result['finished'] is True
    interview.refresh_from_db()
    assert interview.status == 'terminated'

@pytest.mark.django_db
def test_evaluator_produces_binary_result(interview):
    ''' Evaluate every configured criterion and produce a binary outcome. '''
    ConversationTurn.objects.create(interview=interview, role='user', text='I built a Python backend with a SQL database and REST API.')
    interview.status = 'completed'
    interview.save(update_fields=['status'])

    assert evaluate_interview(interview.id) is True
    interview.refresh_from_db()
    assert interview.result in ['PROGRESS', 'NOT_PROGRESS']
    assert interview.evaluation_answers.count() == len(get_evaluation_questions())

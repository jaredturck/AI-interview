''' Verify candidate authentication, vacancy application workflow, ownership and human-review HTTP APIs. '''

import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from interviews.models import ConversationTurn, EvaluationAnswer, HumanReviewRequest, InterviewSession, Job, JobApplication
from interviews.services.interview import INTERVIEW_MAX_MINUTES

User = get_user_model()

def create_user(email='candidate@example.com', password='A-strong-test-password-42'):
    ''' Create a valid email and password Django user for endpoint ownership tests. '''
    return User.objects.create_user(username=email, email=email, password=password)

def create_job(status='open'):
    ''' Create a role-neutral Job snapshot for candidate API tests. '''
    return Job.objects.create(title='Commercial Cleaner', subtitle='Facilities Team', description='Clean commercial facilities.',
        essential_requirements='Demonstrates safe working practices', verification_requirements='Current site access certification',
        evaluation_questions='Reliability evidence\nSafe working evidence', status=status)

@pytest.mark.django_db
def test_signup_creates_authenticated_candidate():
    ''' Verify signup creates both the candidate account and authenticated Django session. '''
    client = Client()
    response = client.post('/api/auth/signup/', data=json.dumps({'email': 'candidate@example.com', 'password': 'A-strong-test-password-42'}),
        content_type='application/json')
    assert response.status_code == 201
    assert response.json()['authenticated'] is True
    assert User.objects.filter(username='candidate@example.com').exists()

@pytest.mark.django_db
def test_non_object_json_is_rejected_without_server_error():
    ''' Verify valid JSON arrays cannot break endpoints that expect an object payload. '''
    client = Client()
    response = client.post('/api/auth/signup/', data='[]', content_type='application/json')
    assert response.status_code == 400

@pytest.mark.django_db
def test_jobs_require_authentication():
    ''' Verify anonymous clients cannot enumerate candidate vacancies or applications. '''
    client = Client()
    response = client.get('/api/jobs/')
    assert response.status_code == 401
    assert response.json()['code'] == 'authentication_required'

@pytest.mark.django_db
def test_job_listing_contains_only_open_jobs():
    ''' Verify the candidate catalogue excludes closed vacancies. '''
    user = create_user()
    open_job = create_job()
    create_job(status='closed')
    client = Client()
    client.force_login(user)
    response = client.get('/api/jobs/')
    assert response.status_code == 200
    assert [item['id'] for item in response.json()['jobs']] == [str(open_job.id)]

@pytest.mark.django_db
def test_job_detail_does_not_expose_hidden_recruitment_rubric():
    ''' Verify candidate APIs expose the public job description without leaking internal evidence or verification criteria. '''
    user = create_user()
    job = create_job()
    client = Client()
    client.force_login(user)
    response = client.get(f'/api/jobs/{job.id}/')
    payload = response.json()['job']
    assert response.status_code == 200
    assert payload['description'] == job.description
    assert 'essential_requirements' not in payload
    assert 'verification_requirements' not in payload
    assert 'evaluation_questions' not in payload
    assert 'sample_key' not in payload

@pytest.mark.django_db
def test_candidate_can_apply_once_and_start_application_interview():
    ''' Verify applying is idempotent and interview creation is scoped to the resulting application. '''
    user = create_user()
    job = create_job()
    client = Client()
    client.force_login(user)
    first = client.post(f'/api/jobs/{job.id}/apply/', data='{}', content_type='application/json')
    second = client.post(f'/api/jobs/{job.id}/apply/', data='{}', content_type='application/json')
    assert first.status_code == 201
    assert second.status_code == 200
    application_id = first.json()['application']['id']
    assert first.json()['application']['id'] == second.json()['application']['id']
    assert JobApplication.objects.filter(user=user, job=job).count() == 1

    started = client.post(f'/api/applications/{application_id}/interview/start/', data=json.dumps({'confirm_transcript': True}),
        content_type='application/json')
    assert started.status_code == 201
    interview = InterviewSession.objects.get(id=started.json()['interview']['id'])
    assert str(interview.application_id) == application_id
    assert interview.confirm_transcript is True
    repeated = client.post(f'/api/applications/{application_id}/interview/start/', data='{}', content_type='application/json')
    assert repeated.status_code == 200
    assert repeated.json()['interview']['id'] == str(interview.id)
    assert InterviewSession.objects.filter(application_id=application_id).count() == 1

@pytest.mark.django_db
def test_application_and_interview_are_private_to_candidate():
    ''' Verify another authenticated candidate cannot inspect application or interview resources by UUID. '''
    owner = create_user()
    other = create_user('other@example.com')
    job = create_job()
    application = JobApplication.objects.create(user=owner, job=job)
    interview = InterviewSession.objects.create(application=application)
    client = Client()
    client.force_login(other)
    assert client.get(f'/api/applications/{application.id}/').status_code == 404
    assert client.get(f'/api/interviews/{interview.id}/status/').status_code == 404

@pytest.mark.django_db
def test_interview_status_exposes_server_authoritative_remaining_time():
    ''' Verify the live UI can initialize its countdown without trusting the browser clock or hidden recruitment data. '''
    user = create_user()
    job = create_job()
    application = JobApplication.objects.create(user=user, job=job, status='interview_in_progress')
    interview = InterviewSession.objects.create(application=application, status='active', started_at=timezone.now() - timedelta(minutes=2))
    client = Client()
    client.force_login(user)
    response = client.get(f'/api/interviews/{interview.id}/status/')
    payload = response.json()
    assert response.status_code == 200
    assert payload['max_minutes'] == INTERVIEW_MAX_MINUTES
    assert INTERVIEW_MAX_MINUTES * 60 - 125 <= payload['remaining_seconds'] <= INTERVIEW_MAX_MINUTES * 60 - 115
    assert 'essential_requirements' not in payload['job']

@pytest.mark.django_db
def test_account_lists_candidate_applications_with_jobs():
    ''' Verify the dashboard response centres applications and includes linked vacancy metadata. '''
    user = create_user()
    job = create_job()
    JobApplication.objects.create(user=user, job=job)
    client = Client()
    client.force_login(user)
    response = client.get('/api/account/')
    assert response.status_code == 200
    assert len(response.json()['applications']) == 1
    assert response.json()['applications'][0]['job']['title'] == 'Commercial Cleaner'

@pytest.mark.django_db
def test_closed_job_stays_visible_to_existing_applicant_but_rejects_new_application():
    ''' Verify closing a vacancy preserves applicant access while preventing new candidates from applying. '''
    owner = create_user()
    other = create_user('other@example.com')
    job = create_job(status='closed')
    JobApplication.objects.create(user=owner, job=job)
    client = Client()
    client.force_login(owner)
    assert client.get(f'/api/jobs/{job.id}/').status_code == 200
    client.force_login(other)
    assert client.get(f'/api/jobs/{job.id}/').status_code == 404
    denied = client.post(f'/api/jobs/{job.id}/apply/', data='{}', content_type='application/json')
    assert denied.status_code == 409

@pytest.mark.django_db
def test_review_request_after_evaluation():
    ''' Verify an evaluated candidate can submit a persisted human-review explanation. '''
    user = create_user()
    job = create_job()
    application = JobApplication.objects.create(user=user, job=job, status='complete')
    interview = InterviewSession.objects.create(application=application, status='evaluated', result='NOT_PROGRESS')
    client = Client()
    client.force_login(user)
    review = client.post(f'/api/interviews/{interview.id}/review/', data=json.dumps({'explanation': 'The microphone failed.'}),
        content_type='application/json')
    assert review.status_code == 201
    assert interview.review_request.explanation == 'The microphone failed.'

@pytest.mark.django_db
def test_missing_job_returns_json_error():
    ''' Verify candidate API failures remain JSON rather than falling through to Django HTML error pages. '''
    user = create_user()
    client = Client()
    client.force_login(user)
    response = client.post('/api/jobs/00000000-0000-0000-0000-000000000000/apply/', data='{}', content_type='application/json')
    assert response.status_code == 404
    assert response.json()['code'] == 'job_not_found'

@pytest.mark.django_db
def test_transcript_download_contains_only_owned_transcript_data():
    ''' Verify the CSV export includes transcript context without exposing automated outcome data or another candidate. '''
    user = create_user()
    other = create_user('other@example.com')
    job = create_job()
    application = JobApplication.objects.create(user=user, job=job, status='complete')
    interview = InterviewSession.objects.create(application=application, status='evaluated', result='PROGRESS')
    ConversationTurn.objects.create(interview=interview, role='assistant', text='Tell me about your previous role.')
    ConversationTurn.objects.create(interview=interview, role='user', text='I supervised an evening facilities team.')
    other_application = JobApplication.objects.create(user=other, job=job)
    other_interview = InterviewSession.objects.create(application=other_application)
    ConversationTurn.objects.create(interview=other_interview, role='user', text='Private answer from another candidate.')
    client = Client()
    client.force_login(user)
    response = client.get('/api/account/transcripts/')
    content = response.content.decode('utf-8')
    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/csv')
    assert 'Commercial Cleaner' in content
    assert 'I supervised an evening facilities team.' in content
    assert 'Private answer from another candidate.' not in content
    assert 'PROGRESS' not in content

@pytest.mark.django_db
def test_candidate_can_delete_one_interview_and_withdraw_that_application():
    ''' Verify one interview deletion removes its evidence, withdraws that application and leaves other applications intact. '''
    user = create_user()
    first_job = create_job()
    second_job = Job.objects.create(title='Warehouse Operative', subtitle='Operations', description='Support warehouse operations.',
        evaluation_questions='Reliability evidence')
    application = JobApplication.objects.create(user=user, job=first_job, status='complete')
    interview = InterviewSession.objects.create(application=application, status='evaluated', result='NOT_PROGRESS')
    ConversationTurn.objects.create(interview=interview, role='user', text='Sensitive employment history.')
    EvaluationAnswer.objects.create(interview=interview, question_index=0, question='Reliability evidence', answer='Assessment evidence')
    HumanReviewRequest.objects.create(interview=interview, explanation='Please review this interview.')
    other_application = JobApplication.objects.create(user=user, job=second_job)
    client = Client()
    client.force_login(user)
    response = client.post(f'/api/interviews/{interview.id}/delete/', data='{}', content_type='application/json')
    assert response.status_code == 200
    assert response.json()['deleted'] is True
    assert User.objects.filter(id=user.id).exists()
    application.refresh_from_db()
    assert application.status == 'withdrawn'
    assert not InterviewSession.objects.filter(id=interview.id).exists()
    assert JobApplication.objects.filter(id=other_application.id).exists()
    reapplied = client.post(f'/api/jobs/{first_job.id}/apply/', data='{}', content_type='application/json')
    restarted = client.post(f'/api/applications/{application.id}/interview/start/', data='{}', content_type='application/json')
    assert reapplied.status_code == 200
    assert reapplied.json()['application']['id'] == str(application.id)
    assert reapplied.json()['application']['status'] == 'withdrawn'
    assert restarted.status_code == 409
    assert restarted.json()['code'] == 'application_withdrawn'

@pytest.mark.django_db
def test_candidate_can_delete_all_recruitment_data_without_deleting_account():
    ''' Verify delete-all removes every application and dependent interview record while preserving authentication data. '''
    user = create_user()
    job = create_job()
    application = JobApplication.objects.create(user=user, job=job, status='complete')
    interview = InterviewSession.objects.create(application=application, status='evaluated', result='PROGRESS')
    ConversationTurn.objects.create(interview=interview, role='user', text='Sensitive employment history.')
    EvaluationAnswer.objects.create(interview=interview, question_index=0, question='Reliability evidence', answer='Assessment evidence')
    HumanReviewRequest.objects.create(interview=interview, explanation='Please review this interview.')
    client = Client()
    client.force_login(user)
    response = client.post('/api/account/interview-data/delete/', data='{}', content_type='application/json')
    assert response.status_code == 200
    assert response.json()['deleted'] is True
    assert User.objects.filter(id=user.id, username='candidate@example.com').exists()
    assert not JobApplication.objects.filter(user=user).exists()
    assert not InterviewSession.objects.filter(application__user=user).exists()

@pytest.mark.django_db
def test_candidate_cannot_delete_another_candidates_interview():
    ''' Verify destructive interview endpoints enforce the same candidate ownership boundary as read endpoints. '''
    owner = create_user()
    other = create_user('other@example.com')
    job = create_job()
    application = JobApplication.objects.create(user=owner, job=job)
    interview = InterviewSession.objects.create(application=application)
    client = Client()
    client.force_login(other)
    response = client.post(f'/api/interviews/{interview.id}/delete/', data='{}', content_type='application/json')
    assert response.status_code == 404
    assert InterviewSession.objects.filter(id=interview.id).exists()

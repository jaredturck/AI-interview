''' Verify the custom recruitment admin dashboard and database-authored immutable vacancy workflow. '''

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from interviews.models import InterviewSession, Job, JobApplication

User = get_user_model()

@pytest.fixture
def admin_client(db):
    ''' Provide an authenticated recruitment administrator for staff workflow tests. '''
    user = User.objects.create_superuser(username='admin@example.com', email='admin@example.com', password='A-strong-test-password-42')
    client = Client()
    client.force_login(user)
    return client, user

@pytest.mark.django_db
def test_recruitment_dashboard_uses_custom_admin_site(admin_client):
    ''' Verify a superuser reaches the recruitment dashboard with ordinary database-backed job creation. '''
    client, _user = admin_client
    response = client.get('/admin/')
    assert response.status_code == 200
    assert b'Recruitment dashboard' in response.content
    assert b'Create job' in response.content
    assert b'Create job from configuration' not in response.content
    assert b'/admin/interviews/job/add/' in response.content

@pytest.mark.django_db
def test_staff_without_job_add_permission_cannot_see_or_open_create_job():
    ''' Verify the custom admin chrome does not advertise a vacancy write action that Django permissions deny. '''
    user = User.objects.create_user(username='viewer@example.com', email='viewer@example.com', password='A-strong-test-password-42', is_staff=True)
    client = Client()
    client.force_login(user)
    dashboard = client.get('/admin/')
    denied = client.get('/admin/interviews/job/add/')
    assert dashboard.status_code == 200
    assert b'/admin/interviews/job/add/' not in dashboard.content
    assert denied.status_code == 403

@pytest.mark.django_db
def test_admin_creates_job_from_textareas(admin_client):
    ''' Verify staff can author the complete recruitment specification directly through the normal Job add form. '''
    client, _user = admin_client
    response = client.post('/admin/interviews/job/add/', data={
        'title': 'Commercial Cleaner',
        'subtitle': 'Facilities Team',
        'description': 'Maintain offices and shared facilities to a safe and consistent standard.',
        'essential_requirements': 'Demonstrates safe cleaning practices\nDemonstrates reliable practical work',
        'verification_requirements': '',
        'evaluation_questions': 'Evidence of hygiene awareness\nEvidence of independent working',
        'status': 'open',
        '_save': 'Save',
    }, follow=False)
    assert response.status_code == 302
    job = Job.objects.get()
    assert job.status == 'open'
    assert job.title == 'Commercial Cleaner'
    assert job.is_sample is False
    assert job.sample_key is None
    assert job.description.startswith('Maintain offices')
    assert job.essential_requirement_list() == ['Demonstrates safe cleaning practices', 'Demonstrates reliable practical work']

@pytest.mark.django_db
def test_admin_rejects_job_without_interview_specification(admin_client):
    ''' Verify staff cannot accidentally publish a job that gives the interviewer no essential or evaluation evidence targets. '''
    client, _user = admin_client
    response = client.post('/admin/interviews/job/add/', data={
        'title': 'Incomplete Job',
        'subtitle': '',
        'description': 'A real description.',
        'essential_requirements': '',
        'verification_requirements': '',
        'evaluation_questions': '',
        'status': 'open',
        '_save': 'Save',
    })
    assert response.status_code == 200
    assert not Job.objects.exists()
    assert b'Enter at least one essential requirement.' in response.content
    assert b'Enter at least one evaluation criterion.' in response.content

@pytest.mark.django_db
def test_job_specification_becomes_read_only_after_application(admin_client):
    ''' Verify the recruitment snapshot cannot be rewritten after a candidate has applied while status remains editable. '''
    client, user = admin_client
    job = Job.objects.create(title='Backend Developer', subtitle='Python', description='Build backend services.',
        essential_requirements='Demonstrates backend development competence', evaluation_questions='Evidence of debugging ability')
    JobApplication.objects.create(user=user, job=job)
    response = client.get(f'/admin/interviews/job/{job.pk}/change/')
    assert response.status_code == 200
    assert b'name="description"' not in response.content
    assert b'name="essential_requirements"' not in response.content
    assert b'name="evaluation_questions"' not in response.content
    assert b'name="status"' in response.content
    assert b'Build backend services.' in response.content

@pytest.mark.django_db
def test_locked_job_can_still_change_status(admin_client):
    ''' Verify readonly recruitment fields do not make the admin form invalid when staff close a used vacancy. '''
    client, user = admin_client
    job = Job.objects.create(title='Used Job', description='Immutable role content.',
        essential_requirements='Demonstrates the core skill', evaluation_questions='Evidence of the core skill')
    JobApplication.objects.create(user=user, job=job)
    response = client.post(f'/admin/interviews/job/{job.pk}/change/', data={'status': 'closed', '_save': 'Save'}, follow=False)
    job.refresh_from_db()
    assert response.status_code == 302
    assert job.status == 'closed'
    assert job.description == 'Immutable role content.'

@pytest.mark.django_db
def test_unused_job_change_form_has_delete_action(admin_client):
    ''' Verify an unused test or sample vacancy can be removed through normal Django admin deletion. '''
    client, _user = admin_client
    job = Job.objects.create(title='Disposable Test Job', description='Temporary test role.',
        essential_requirements='Demonstrates the required skill', evaluation_questions='Evidence of the required skill')
    response = client.get(f'/admin/interviews/job/{job.pk}/change/')
    assert response.status_code == 200
    assert f'/admin/interviews/job/{job.pk}/delete/'.encode() in response.content
    assert b'class="deletelink"' in response.content

@pytest.mark.django_db
def test_interview_session_change_form_keeps_superuser_delete_action(admin_client):
    ''' Verify read-only interview evidence can still be deleted through Django's normal protected delete flow. '''
    client, user = admin_client
    job = Job.objects.create(title='Backend Software Developer', subtitle='Test role', description='Test description',
        essential_requirements='Technical competence', evaluation_questions='Technical evidence')
    application = JobApplication.objects.create(user=user, job=job)
    interview = InterviewSession.objects.create(application=application)
    response = client.get(f'/admin/interviews/interviewsession/{interview.pk}/change/')
    assert response.status_code == 200
    assert f'/admin/interviews/interviewsession/{interview.pk}/delete/'.encode() in response.content
    assert b'class="deletelink"' in response.content

@pytest.mark.django_db
def test_admin_change_list_uses_redesigned_shell_and_final_stylesheet(admin_client):
    ''' Verify stock changelist behavior is wrapped by the custom top navigation and final visual layer. '''
    client, _user = admin_client
    response = client.get('/admin/auth/user/')
    assert response.status_code == 200
    assert b'class="admin-primary-nav"' in response.content
    assert b'id="nav-sidebar"' not in response.content
    assert b'class="changelist-surface' in response.content
    assert b'class="admin-filter-panel"' in response.content
    assert response.content.index(b'admin/css/changelists.css') < response.content.index(b'admin/css/recruitment_admin.css')

@pytest.mark.django_db
def test_admin_change_form_uses_redesigned_fieldsets_without_losing_form_contracts(admin_client):
    ''' Verify change forms keep Django's form hooks while using the redesigned field and action surfaces. '''
    client, user = admin_client
    response = client.get(f'/admin/auth/user/{user.pk}/change/')
    assert response.status_code == 200
    assert b'id="user_form"' in response.content
    assert b'class="module aligned admin-fieldset' in response.content
    assert b'class="submit-row"' in response.content
    assert response.content.index(b'admin/css/forms.css') < response.content.index(b'admin/css/recruitment_admin.css')

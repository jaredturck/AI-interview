''' Verify the custom recruitment admin dashboard and staff-controlled vacancy creation workflow. '''

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from interviews.models import InterviewSession, Job, JobApplication

User = get_user_model()

@pytest.mark.django_db
def test_recruitment_dashboard_uses_custom_admin_site():
    ''' Verify a superuser reaches the recruitment-specific dashboard rather than the stock Django index. '''
    user = User.objects.create_superuser(username='admin@example.com', email='admin@example.com', password='A-strong-test-password-42')
    client = Client()
    client.force_login(user)
    response = client.get('/admin/')
    assert response.status_code == 200
    assert b'Recruitment dashboard' in response.content
    assert b'Create job from configuration' in response.content

@pytest.mark.django_db
def test_admin_creates_open_job_from_configuration(monkeypatch):
    ''' Verify the staff-only admin action snapshots configuration and opens the generated vacancy. '''
    user = User.objects.create_superuser(username='admin@example.com', email='admin@example.com', password='A-strong-test-password-42')
    description = '# Cleaner\nMaintain commercial facilities.'
    questions = 'Reliability evidence\nSafety evidence'
    monkeypatch.setattr('interviews.services.jobs.get_job_configuration', lambda: (description, questions))
    client = Client()
    client.force_login(user)
    response = client.post('/admin/jobs/create-from-configuration/', follow=False)
    assert response.status_code == 302
    job = Job.objects.get()
    assert job.status == 'open'
    assert job.title == 'Commercial Cleaner'
    assert job.description == description
    assert job.evaluation_questions == questions


@pytest.mark.django_db
def test_interview_session_change_form_keeps_superuser_delete_action():
    ''' Verify read-only interview evidence can still be deleted through Django's normal protected delete flow. '''
    user = User.objects.create_superuser(username='admin@example.com', email='admin@example.com', password='A-strong-test-password-42')
    job = Job.objects.create(
        title='Backend Software Developer',
        subtitle='Test role',
        description='Test description',
        evaluation_questions='Technical evidence',
    )
    application = JobApplication.objects.create(user=user, job=job)
    interview = InterviewSession.objects.create(application=application)
    client = Client()
    client.force_login(user)
    response = client.get(f'/admin/interviews/interviewsession/{interview.pk}/change/')
    assert response.status_code == 200
    assert f'/admin/interviews/interviewsession/{interview.pk}/delete/'.encode() in response.content
    assert b'class="deletelink"' in response.content

@pytest.mark.django_db
def test_admin_change_list_uses_redesigned_shell_and_final_stylesheet():
    ''' Verify stock changelist behavior is wrapped by the custom top navigation and final visual layer. '''
    user = User.objects.create_superuser(username='admin@example.com', email='admin@example.com', password='A-strong-test-password-42')
    client = Client()
    client.force_login(user)
    response = client.get('/admin/auth/user/')
    assert response.status_code == 200
    assert b'class="admin-primary-nav"' in response.content
    assert b'id="nav-sidebar"' not in response.content
    assert b'class="changelist-surface' in response.content
    assert b'class="admin-filter-panel"' in response.content
    assert response.content.index(b'admin/css/changelists.css') < response.content.index(b'admin/css/recruitment_admin.css')

@pytest.mark.django_db
def test_admin_change_form_uses_redesigned_fieldsets_without_losing_form_contracts():
    ''' Verify change forms keep Django's form hooks while using the redesigned field and action surfaces. '''
    user = User.objects.create_superuser(username='admin@example.com', email='admin@example.com', password='A-strong-test-password-42')
    client = Client()
    client.force_login(user)
    response = client.get(f'/admin/auth/user/{user.pk}/change/')
    assert response.status_code == 200
    assert b'id="user_form"' in response.content
    assert b'class="module aligned admin-fieldset' in response.content
    assert b'class="submit-row"' in response.content
    assert response.content.index(b'admin/css/forms.css') < response.content.index(b'admin/css/recruitment_admin.css')

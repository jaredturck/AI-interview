''' Verify the custom recruitment admin dashboard and staff-controlled vacancy creation workflow. '''

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from interviews.models import Job

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

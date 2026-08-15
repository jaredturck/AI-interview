''' Verify optional research-backed sample vacancies can be seeded without weakening immutable recruitment snapshots. '''

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from interviews.models import Job, JobApplication
from interviews.sample_jobs import SAMPLE_JOBS

User = get_user_model()

def test_sample_job_fixture_has_ten_complete_distinct_roles():
    ''' Verify the source-controlled demo set remains broad and every role has enough evidence targets to exercise the interviewer. '''
    keys = [sample['sample_key'] for sample in SAMPLE_JOBS]
    titles = [sample['title'] for sample in SAMPLE_JOBS]
    assert len(SAMPLE_JOBS) == 10
    assert len(keys) == len(set(keys))
    assert len(titles) == len(set(titles))

    for sample in SAMPLE_JOBS:
        assert sample['description'].strip()
        assert len(sample['essential_requirements'].splitlines()) >= 4
        assert len(sample['evaluation_questions'].splitlines()) >= 6

@pytest.mark.django_db
def test_seed_sample_jobs_is_idempotent():
    ''' Verify repeated normal seeding creates exactly one database row for each canonical sample key. '''
    call_command('seed_sample_jobs')
    call_command('seed_sample_jobs')
    assert Job.objects.filter(is_sample=True).count() == len(SAMPLE_JOBS)
    assert Job.objects.exclude(sample_key__isnull=True).count() == len(SAMPLE_JOBS)
    assert Job.objects.values('sample_key').distinct().count() == len(SAMPLE_JOBS)

@pytest.mark.django_db
def test_reset_restores_unused_sample_job():
    ''' Verify explicit reset restores edited demo data when no candidate has made it an immutable recruitment snapshot. '''
    call_command('seed_sample_jobs')
    sample = SAMPLE_JOBS[0]
    job = Job.objects.get(sample_key=sample['sample_key'])
    job.title = 'Edited local title'
    job.description = 'Edited local description'
    job.save(update_fields=['title', 'description'])
    call_command('seed_sample_jobs', reset=True)
    job.refresh_from_db()
    assert job.title == sample['title']
    assert job.description == sample['description']

@pytest.mark.django_db
def test_reset_preserves_sample_job_after_candidate_application():
    ''' Verify reset refuses to rewrite a sample specification after a candidate has applied against it. '''
    call_command('seed_sample_jobs')
    sample = SAMPLE_JOBS[0]
    job = Job.objects.get(sample_key=sample['sample_key'])
    job.title = 'Snapshot title retained for audit'
    job.save(update_fields=['title'])
    user = User.objects.create_user(username='candidate@example.com', email='candidate@example.com', password='A-strong-test-password-42')
    JobApplication.objects.create(user=user, job=job)
    call_command('seed_sample_jobs', reset=True)
    job.refresh_from_db()
    assert job.title == 'Snapshot title retained for audit'

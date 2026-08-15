''' Seed optional research-backed demonstration vacancies for local testing and evaluation. '''

from django.core.management.base import BaseCommand
from django.utils import timezone

from interviews.models import Job
from interviews.sample_jobs import SAMPLE_JOBS

class Command(BaseCommand):
    ''' Create missing sample jobs and optionally restore unused samples to their canonical definitions. '''
    help = 'Create the built-in sample jobs. Existing sample jobs are left unchanged unless --reset is supplied.'

    def add_arguments(self, parser):
        ''' Add an explicit reset mode without making normal seeding destructive. '''
        parser.add_argument('--reset', action='store_true', help='Restore existing unused sample jobs to the built-in definitions.')

    def handle(self, *args, **options):
        ''' Seed every canonical sample once while preserving Job snapshots that already have applications. '''
        created = 0
        restored = 0
        skipped = 0

        for sample in SAMPLE_JOBS:
            sample_title = sample['title']
            job = Job.objects.filter(sample_key=sample['sample_key']).first()

            if not job:
                Job.objects.create(**sample, is_sample=True, status='open', opened_at=timezone.now())
                created += 1
                self.stdout.write(self.style.SUCCESS(f'Created sample job: {sample_title}'))
                continue

            if not options['reset']:
                skipped += 1
                self.stdout.write(f'Skipped existing sample job: {job.title}')
                continue

            if job.applications.exists():
                skipped += 1
                self.stdout.write(self.style.WARNING(f'Skipped used sample snapshot: {job.title}'))
                continue

            for field in ['title', 'subtitle', 'description', 'essential_requirements', 'verification_requirements', 'evaluation_questions']:
                setattr(job, field, sample[field])

            job.is_sample = True
            job.status = 'open'
            job.opened_at = timezone.now()
            job.closed_at = None
            job.save(update_fields=['title', 'subtitle', 'description', 'essential_requirements', 'verification_requirements', 'evaluation_questions',
                'is_sample', 'status', 'opened_at', 'closed_at'])
            restored += 1
            self.stdout.write(self.style.SUCCESS(f'Restored sample job: {job.title}'))

        self.stdout.write(f'Sample jobs complete: {created} created, {restored} restored, {skipped} skipped.')

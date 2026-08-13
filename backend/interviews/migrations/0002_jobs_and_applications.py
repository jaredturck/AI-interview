from pathlib import Path

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
import django.db.models.deletion
import uuid


def migrate_existing_interviews(apps, schema_editor):
    Job = apps.get_model('interviews', 'Job')
    JobApplication = apps.get_model('interviews', 'JobApplication')
    InterviewSession = apps.get_model('interviews', 'InterviewSession')
    project_root = Path(settings.BASE_DIR).parent
    description = (project_root / 'config' / 'job_description.md').read_text(encoding='utf-8').strip()
    evaluation_questions = (project_root / 'config' / 'evaluation_questions.txt').read_text(encoding='utf-8').strip()
    title = 'Legacy job'

    for raw_line in description.splitlines():
        line = raw_line.strip()

        if line.startswith('# '):
            title = line[2:].strip()[:120]
            break

    interviews = list(InterviewSession.objects.order_by('created_at', 'id'))

    if not interviews:
        return

    now = timezone.now()
    shared_job = Job.objects.create(title=title, subtitle='', description=description, evaluation_questions=evaluation_questions,
        status='closed', opened_at=now, closed_at=now)
    seen_users = set()

    for interview in interviews:
        job = shared_job

        if interview.user_id in seen_users:
            job = Job.objects.create(title=title, subtitle='', description=description, evaluation_questions=evaluation_questions,
                status='closed', opened_at=now, closed_at=now)

        seen_users.add(interview.user_id)
        application_status = 'interview_in_progress'

        if interview.status in ['completed', 'terminated', 'evaluating']:
            application_status = 'evaluating'
        elif interview.status in ['evaluated', 'evaluation_failed']:
            application_status = 'complete'

        application = JobApplication.objects.create(user_id=interview.user_id, job=job, status=application_status)
        JobApplication.objects.filter(id=application.id).update(applied_at=interview.created_at)
        interview.application_id = application.id
        interview.save(update_fields=['application'])


class Migration(migrations.Migration):

    dependencies = [
        ('interviews', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=120)),
                ('subtitle', models.CharField(blank=True, max_length=160)),
                ('description', models.TextField()),
                ('evaluation_questions', models.TextField()),
                ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed')], default='open', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('opened_at', models.DateTimeField(default=timezone.now)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Job',
                'verbose_name_plural': 'Jobs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='JobApplication',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('interview_pending', 'Interview pending'), ('interview_in_progress', 'Interview in progress'), ('evaluating', 'Evaluating'), ('complete', 'Complete')], default='interview_pending', max_length=30)),
                ('applied_at', models.DateTimeField(auto_now_add=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='applications', to='interviews.job')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Job application',
                'verbose_name_plural': 'Job applications',
                'ordering': ['-applied_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='jobapplication',
            constraint=models.UniqueConstraint(fields=('user', 'job'), name='unique_user_job_application'),
        ),
        migrations.AlterModelOptions(
            name='interviewsession',
            options={'verbose_name': 'Interview session', 'verbose_name_plural': 'Interview sessions'},
        ),
        migrations.AlterModelOptions(
            name='conversationturn',
            options={'ordering': ['created_at', 'id'], 'verbose_name': 'Conversation turn', 'verbose_name_plural': 'Conversation turns'},
        ),
        migrations.AlterModelOptions(
            name='evaluationanswer',
            options={'ordering': ['question_index'], 'verbose_name': 'Evaluation answer', 'verbose_name_plural': 'Evaluation answers'},
        ),
        migrations.AlterModelOptions(
            name='humanreviewrequest',
            options={'verbose_name': 'Human review request', 'verbose_name_plural': 'Human review requests'},
        ),
        migrations.AddField(
            model_name='interviewsession',
            name='application',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='interview', to='interviews.jobapplication'),
        ),
        migrations.RunPython(migrate_existing_interviews, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='interviewsession',
            name='application',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='interview', to='interviews.jobapplication'),
        ),
        migrations.RemoveField(
            model_name='interviewsession',
            name='user',
        ),
    ]

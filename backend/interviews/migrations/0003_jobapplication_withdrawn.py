from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interviews', '0002_jobs_and_applications'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobapplication',
            name='status',
            field=models.CharField(choices=[('interview_pending', 'Interview pending'), ('interview_in_progress', 'Interview in progress'), ('evaluating', 'Evaluating'), ('complete', 'Complete'), ('withdrawn', 'Withdrawn')], default='interview_pending', max_length=30),
        ),
    ]

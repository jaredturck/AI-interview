from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interviews', '0004_job_recruitment_specification'),
    ]

    operations = [
        migrations.AddField(
            model_name='interviewsession',
            name='phase',
            field=models.CharField(choices=[('main', 'Main interview'), ('wrap_up', 'Wrap up')], default='main', max_length=20),
        ),
    ]

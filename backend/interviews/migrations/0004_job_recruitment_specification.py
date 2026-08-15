from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interviews', '0003_jobapplication_withdrawn'),
    ]

    operations = [
        migrations.AddField(
            model_name='evaluationanswer',
            name='assessment',
            field=models.CharField(blank=True, choices=[('', 'Legacy / not classified'), ('MET', 'Met'), ('PARTIALLY_MET', 'Partially met'), ('NOT_MET', 'Not met'), ('INSUFFICIENT_EVIDENCE', 'Insufficient evidence'), ('CONTRADICTORY_EVIDENCE', 'Contradictory evidence'), ('POSITIVE', 'Positive evidence'), ('MIXED', 'Mixed evidence'), ('NEGATIVE', 'Negative evidence'), ('CLAIMED', 'Claimed'), ('NOT_CLAIMED', 'Not claimed'), ('UNCLEAR', 'Unclear')], default='', max_length=30),
        ),
        migrations.AddField(
            model_name='evaluationanswer',
            name='criterion_type',
            field=models.CharField(choices=[('essential', 'Essential requirement'), ('verification', 'Verification requirement'), ('evaluation', 'Evaluation criterion')], default='evaluation', max_length=20),
        ),
        migrations.AddField(
            model_name='job',
            name='essential_requirements',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='job',
            name='is_sample',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='job',
            name='sample_key',
            field=models.SlugField(blank=True, max_length=80, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='job',
            name='verification_requirements',
            field=models.TextField(blank=True, default=''),
        ),
    ]

import django.db.models.deletion
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CompanyDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("content", models.TextField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Job",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField()),
                ("evaluation_questions", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="InterviewSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("candidate_name", models.CharField(blank=True, max_length=200)),
                ("candidate_email", models.EmailField(blank=True, max_length=254)),
                ("language", models.CharField(default="English", max_length=40)),
                ("confirm_transcript", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("created", "Created"), ("active", "Active"), ("completed", "Completed"), ("terminated", "Terminated"), ("evaluating", "Evaluating"), ("evaluated", "Evaluated"), ("evaluation_failed", "Evaluation failed")], default="created", max_length=20)),
                ("result", models.CharField(blank=True, choices=[("", "Pending"), ("PROGRESS", "Progress"), ("NOT_PROGRESS", "Not progress")], max_length=20)),
                ("access_token_hash", models.CharField(max_length=64)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="interviews.job")),
            ],
        ),
        migrations.CreateModel(
            name="ConversationTurn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("assistant", "Assistant"), ("user", "User")], max_length=20)),
                ("text", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("interview", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="turns", to="interviews.interviewsession")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.CreateModel(
            name="EvaluationAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_index", models.PositiveIntegerField()),
                ("question", models.TextField()),
                ("answer", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("interview", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evaluation_answers", to="interviews.interviewsession")),
            ],
            options={"ordering": ["question_index"]},
        ),
        migrations.CreateModel(
            name="HumanReviewRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("email", models.EmailField(max_length=254)),
                ("explanation", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("interview", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="review_requests", to="interviews.interviewsession")),
            ],
        ),
        migrations.AddConstraint(
            model_name="evaluationanswer",
            constraint=models.UniqueConstraint(fields=("interview", "question_index"), name="unique_interview_question"),
        ),
    ]

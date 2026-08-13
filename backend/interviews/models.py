import hashlib
import secrets
import uuid

from django.db import models


class Job(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    evaluation_questions = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class CompanyDocument(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class InterviewSession(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("terminated", "Terminated"),
        ("evaluating", "Evaluating"),
        ("evaluated", "Evaluated"),
        ("evaluation_failed", "Evaluation failed"),
    ]

    RESULT_CHOICES = [
        ("", "Pending"),
        ("PROGRESS", "Progress"),
        ("NOT_PROGRESS", "Not progress"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.PROTECT)
    candidate_name = models.CharField(max_length=200, blank=True)
    candidate_email = models.EmailField(blank=True)
    language = models.CharField(max_length=40, default="English")
    confirm_transcript = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, blank=True)
    access_token_hash = models.CharField(max_length=64)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def issue_access_token(self):
        token = secrets.token_urlsafe(32)
        self.access_token_hash = hashlib.sha256(token.encode()).hexdigest()
        return token

    def token_matches(self, token):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return secrets.compare_digest(self.access_token_hash, token_hash)

    def __str__(self):
        return f"{self.job.title} - {self.id}"


class ConversationTurn(models.Model):
    ROLE_CHOICES = [
        ("assistant", "Assistant"),
        ("user", "User"),
    ]

    interview = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name="turns")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.text[:60]}"


class EvaluationAnswer(models.Model):
    interview = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name="evaluation_answers")
    question_index = models.PositiveIntegerField()
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["question_index"]
        constraints = [
            models.UniqueConstraint(fields=["interview", "question_index"], name="unique_interview_question")
        ]


class HumanReviewRequest(models.Model):
    interview = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name="review_requests")
    name = models.CharField(max_length=200)
    email = models.EmailField()
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review request for {self.interview_id}"

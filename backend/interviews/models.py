''' Database models for interview runtime data and evaluation results. '''
import hashlib, secrets, uuid

from django.db import models

class InterviewSession(models.Model):
    ''' Store one candidate interview session. '''
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
        ('evaluating', 'Evaluating'),
        ('evaluated', 'Evaluated'),
        ('evaluation_failed', 'Evaluation failed'),
    ]
    RESULT_CHOICES = [
        ('', 'Pending'),
        ('PROGRESS', 'Progress'),
        ('NOT_PROGRESS', 'Not progress'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate_name = models.CharField(max_length=200, blank=True)
    candidate_email = models.EmailField(blank=True)
    language = models.CharField(max_length=40, default='English')
    confirm_transcript = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, blank=True)
    access_token_hash = models.CharField(max_length=64)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def issue_access_token(self):
        ''' Create and store a hashed access token for the interview. '''
        token = secrets.token_urlsafe(32)
        self.access_token_hash = hashlib.sha256(token.encode()).hexdigest()
        return token

    def token_matches(self, token):
        ''' Return whether a supplied access token belongs to the interview. '''
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return secrets.compare_digest(self.access_token_hash, token_hash)

    def __str__(self):
        ''' Return a readable interview identifier. '''
        return f'{self.candidate_name or "Candidate"} - {self.id}'

class ConversationTurn(models.Model):
    ''' Store one text turn from the candidate or interviewer. '''
    ROLE_CHOICES = [('assistant', 'Assistant'), ('user', 'User')]

    interview = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='turns')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ''' Define stable transcript ordering. '''
        ordering = ['created_at', 'id']

    def __str__(self):
        ''' Return a short transcript preview. '''
        return f'{self.role}: {self.text[:60]}'

class EvaluationAnswer(models.Model):
    ''' Store the evaluator assessment for one configured criterion. '''
    interview = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='evaluation_answers')
    question_index = models.PositiveIntegerField()
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ''' Order criterion assessments and prevent duplicate positions. '''
        ordering = ['question_index']
        constraints = [models.UniqueConstraint(fields=['interview', 'question_index'], name='unique_interview_question')]

    def __str__(self):
        ''' Return a readable criterion identifier. '''
        return f'{self.interview_id} criterion {self.question_index + 1}'

class HumanReviewRequest(models.Model):
    ''' Store a candidate request for human review. '''
    interview = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='review_requests')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        ''' Return a readable review request identifier. '''
        return f'Review request for {self.interview_id}'

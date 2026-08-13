''' Database models for interview runtime data and evaluation results. '''

import uuid

from django.conf import settings
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='interviews')
    confirm_transcript = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        ''' Return a readable interview identifier. '''
        return f'{self.user.email} - {self.id}'

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
    interview = models.OneToOneField(InterviewSession, on_delete=models.CASCADE, related_name='review_request')
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        ''' Return a readable review request identifier. '''
        return f'Review request for {self.interview_id}'

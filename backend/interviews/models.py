''' Persist interview lifecycle, transcript evidence, evaluator assessments and human-review requests. '''

import uuid

from django.conf import settings
from django.db import models

class InterviewSession(models.Model):
    ''' Track one candidate interview from creation through evaluation, including transcript confirmation and final outcome. '''
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
        ''' Identify interview sessions by the candidate's email and UUID in Django admin and logs. '''
        return f'{self.user.email} - {self.id}'

class ConversationTurn(models.Model):
    ''' Preserve candidate and interviewer text as ordered evidence for prompts, evaluation and human review. '''
    ROLE_CHOICES = [('assistant', 'Assistant'), ('user', 'User')]

    interview = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='turns')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ''' Keep transcript evidence in stable chronological order when timestamps match. '''
        ordering = ['created_at', 'id']

    def __str__(self):
        ''' Make transcript records identifiable by speaker and a short text preview in admin and logs. '''
        return f'{self.role}: {self.text[:60]}'

class EvaluationAnswer(models.Model):
    ''' Preserve the Qwen3.6 assessment for one configured criterion as auditable evaluation evidence. '''
    interview = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='evaluation_answers')
    question_index = models.PositiveIntegerField()
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ''' Keep criterion evidence in rubric order and prevent duplicate positions within an interview. '''
        ordering = ['question_index']
        constraints = [models.UniqueConstraint(fields=['interview', 'question_index'], name='unique_interview_question')]

    def __str__(self):
        ''' Identify stored criterion assessments by interview and one-based rubric position in admin and logs. '''
        return f'{self.interview_id} criterion {self.question_index + 1}'

class HumanReviewRequest(models.Model):
    ''' Record the candidate's explanation when asking a person to review automated interview processing. '''
    interview = models.OneToOneField(InterviewSession, on_delete=models.CASCADE, related_name='review_request')
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        ''' Identify a human-review request by its interview in admin and logs. '''
        return f'Review request for {self.interview_id}'

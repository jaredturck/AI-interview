''' Persist jobs, applications, interview lifecycle, transcript evidence, evaluator assessments and review requests. '''

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Job(models.Model):
    ''' Preserve one immutable recruitment configuration snapshot and its candidate-facing metadata. '''
    STATUS_CHOICES = [
        ('open', _('Open')),
        ('closed', _('Closed')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=120)
    subtitle = models.CharField(max_length=160, blank=True)
    description = models.TextField()
    evaluation_questions = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ''' Keep the newest recruitment vacancies first in staff and candidate listings. '''
        ordering = ['-created_at']
        verbose_name = _('Job')
        verbose_name_plural = _('Jobs')

    def __str__(self):
        ''' Identify jobs by their concise candidate-facing title. '''
        return self.title

    def evaluation_question_list(self):
        ''' Return the stored evaluation rubric as ordered non-empty criterion lines. '''
        questions = []

        for raw_line in self.evaluation_questions.splitlines():
            line = raw_line.strip()

            if line:
                questions.append(line)

        return questions

class JobApplication(models.Model):
    ''' Link one candidate to one vacancy and track progress through its AI interview stage. '''
    STATUS_CHOICES = [
        ('interview_pending', _('Interview pending')),
        ('interview_in_progress', _('Interview in progress')),
        ('evaluating', _('Evaluating')),
        ('complete', _('Complete')),
        ('withdrawn', _('Withdrawn')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name='applications')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='interview_pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ''' Prevent duplicate candidate applications while keeping newest applications first. '''
        ordering = ['-applied_at']
        verbose_name = _('Job application')
        verbose_name_plural = _('Job applications')
        constraints = [models.UniqueConstraint(fields=['user', 'job'], name='unique_user_job_application')]

    def __str__(self):
        ''' Identify applications by candidate email and vacancy title. '''
        return f'{self.user.email} - {self.job.title}'

class InterviewSession(models.Model):
    ''' Track one application interview from creation through evaluation and final outcome. '''
    STATUS_CHOICES = [
        ('created', _('Created')),
        ('active', _('Active')),
        ('completed', _('Completed')),
        ('terminated', _('Terminated')),
        ('evaluating', _('Evaluating')),
        ('evaluated', _('Evaluated')),
        ('evaluation_failed', _('Evaluation failed')),
    ]
    RESULT_CHOICES = [
        ('', _('Pending')),
        ('PROGRESS', _('Progress')),
        ('NOT_PROGRESS', _('Not progress')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(JobApplication, on_delete=models.CASCADE, related_name='interview')
    confirm_transcript = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ''' Give interview evidence clear translated names in Django administration. '''
        verbose_name = _('Interview session')
        verbose_name_plural = _('Interview sessions')

    def __str__(self):
        ''' Identify interview sessions by candidate email, vacancy and UUID. '''
        return f'{self.application.user.email} - {self.application.job.title} - {self.id}'

class ConversationTurn(models.Model):
    ''' Preserve candidate and interviewer text as ordered evidence for prompts, evaluation and human review. '''
    ROLE_CHOICES = [('assistant', _('Assistant')), ('user', _('User'))]

    interview = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='turns')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ''' Keep transcript evidence in stable chronological order when timestamps match. '''
        ordering = ['created_at', 'id']
        verbose_name = _('Conversation turn')
        verbose_name_plural = _('Conversation turns')

    def __str__(self):
        ''' Make transcript records identifiable by speaker and a short text preview in admin and logs. '''
        return f'{self.role}: {self.text[:60]}'

class EvaluationAnswer(models.Model):
    ''' Preserve the Qwen3.5-9B assessment for one configured criterion as auditable evaluation evidence. '''
    interview = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='evaluation_answers')
    question_index = models.PositiveIntegerField()
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ''' Keep criterion evidence in rubric order and prevent duplicate positions within an interview. '''
        ordering = ['question_index']
        verbose_name = _('Evaluation answer')
        verbose_name_plural = _('Evaluation answers')
        constraints = [models.UniqueConstraint(fields=['interview', 'question_index'], name='unique_interview_question')]

    def __str__(self):
        ''' Identify stored criterion assessments by interview and one-based rubric position in admin and logs. '''
        return f'{self.interview_id} criterion {self.question_index + 1}'

class HumanReviewRequest(models.Model):
    ''' Record the candidate's explanation when asking a person to review automated interview processing. '''
    interview = models.OneToOneField(InterviewSession, on_delete=models.CASCADE, related_name='review_request')
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ''' Give candidate-requested review evidence clear translated names in Django administration. '''
        verbose_name = _('Human review request')
        verbose_name_plural = _('Human review requests')

    def __str__(self):
        ''' Identify a human-review request by its interview in admin and logs. '''
        return f'Review request for {self.interview_id}'

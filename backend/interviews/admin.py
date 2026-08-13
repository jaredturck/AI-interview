''' Django admin views for interviews, evaluations and review requests. '''
from django.contrib import admin

from interviews.models import ConversationTurn, EvaluationAnswer, HumanReviewRequest, InterviewSession

class ConversationTurnInline(admin.TabularInline):
    ''' Show interview transcript turns as read-only rows. '''
    model = ConversationTurn
    extra = 0
    readonly_fields = ('role', 'text', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        ''' Prevent transcript editing through Django admin. '''
        return False

class EvaluationAnswerInline(admin.TabularInline):
    ''' Show criterion assessments as read-only rows. '''
    model = EvaluationAnswer
    extra = 0
    readonly_fields = ('question_index', 'question', 'answer', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        ''' Prevent evaluation editing through Django admin. '''
        return False

class HumanReviewRequestInline(admin.StackedInline):
    ''' Show candidate review requests as read-only records. '''
    model = HumanReviewRequest
    extra = 0
    readonly_fields = ('name', 'email', 'explanation', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        ''' Prevent review request creation through Django admin. '''
        return False

@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    ''' Present interview sessions and their related evidence. '''
    list_display = ('id', 'status', 'result', 'candidate_name', 'started_at', 'ended_at')
    list_filter = ('status', 'result')
    search_fields = ('candidate_name', 'candidate_email', 'id')
    readonly_fields = (
        'id', 'candidate_name', 'candidate_email', 'language', 'confirm_transcript', 'status', 'result',
        'access_token_hash', 'created_at', 'started_at', 'ended_at'
    )
    inlines = (ConversationTurnInline, EvaluationAnswerInline, HumanReviewRequestInline)

    def has_add_permission(self, request):
        ''' Prevent interview creation through Django admin. '''
        return False

    def has_delete_permission(self, request, obj=None):
        ''' Preserve interview records through Django admin. '''
        return False

@admin.register(HumanReviewRequest)
class HumanReviewRequestAdmin(admin.ModelAdmin):
    ''' Present candidate-requested human reviews. '''
    list_display = ('interview', 'name', 'email', 'created_at')
    search_fields = ('name', 'email', 'interview__id')
    readonly_fields = ('interview', 'name', 'email', 'explanation', 'created_at')

    def has_add_permission(self, request):
        ''' Prevent manual review request creation through Django admin. '''
        return False

    def has_delete_permission(self, request, obj=None):
        ''' Preserve submitted review requests through Django admin. '''
        return False

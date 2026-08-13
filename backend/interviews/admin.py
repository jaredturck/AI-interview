''' Django admin views for interviews, transcripts, evaluations and review requests. '''

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
    readonly_fields = ('explanation', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        ''' Prevent review request creation through Django admin. '''
        return False

@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    ''' Present interview sessions and their related evidence. '''
    list_display = ('id', 'user', 'status', 'result', 'started_at', 'ended_at')
    list_filter = ('status', 'result')
    search_fields = ('user__email', 'id')
    readonly_fields = ('id', 'user', 'confirm_transcript', 'status', 'result', 'created_at', 'started_at', 'ended_at')
    inlines = (ConversationTurnInline, EvaluationAnswerInline, HumanReviewRequestInline)

    def has_add_permission(self, request):
        ''' Prevent interview creation through Django admin. '''
        return False

@admin.register(ConversationTurn)
class ConversationTurnAdmin(admin.ModelAdmin):
    ''' Present stored interview transcript turns. '''
    list_display = ('interview', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('interview__user__email', 'text')
    readonly_fields = ('interview', 'role', 'text', 'created_at')

    def has_add_permission(self, request):
        ''' Prevent transcript creation through Django admin. '''
        return False

@admin.register(EvaluationAnswer)
class EvaluationAnswerAdmin(admin.ModelAdmin):
    ''' Present stored criterion assessments. '''
    list_display = ('interview', 'question_index', 'created_at')
    search_fields = ('interview__user__email', 'question', 'answer')
    readonly_fields = ('interview', 'question_index', 'question', 'answer', 'created_at')

    def has_add_permission(self, request):
        ''' Prevent criterion creation through Django admin. '''
        return False

@admin.register(HumanReviewRequest)
class HumanReviewRequestAdmin(admin.ModelAdmin):
    ''' Present candidate-requested human reviews. '''
    list_display = ('interview', 'candidate_email', 'created_at')
    search_fields = ('interview__user__email', 'explanation')
    readonly_fields = ('interview', 'explanation', 'created_at')

    def candidate_email(self, obj):
        ''' Return the account email for the review request. '''
        return obj.interview.user.email

    def has_add_permission(self, request):
        ''' Prevent manual review request creation through Django admin. '''
        return False

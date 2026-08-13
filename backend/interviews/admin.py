''' Expose immutable interview evidence and candidate review requests to staff through Django admin. '''

from django.contrib import admin

from interviews.models import ConversationTurn, EvaluationAnswer, HumanReviewRequest, InterviewSession

class ConversationTurnInline(admin.TabularInline):
    ''' Keep each interview transcript visible beside its session without allowing staff to alter evidence. '''
    model = ConversationTurn
    extra = 0
    readonly_fields = ('role', 'text', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        ''' Keep transcript evidence immutable by blocking manual turn creation in Django admin. '''
        return False

class EvaluationAnswerInline(admin.TabularInline):
    ''' Keep criterion assessments visible beside their interview without allowing staff to alter evaluator evidence. '''
    model = EvaluationAnswer
    extra = 0
    readonly_fields = ('question_index', 'question', 'answer', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        ''' Keep evaluator evidence immutable by blocking manual criterion creation in Django admin. '''
        return False

class HumanReviewRequestInline(admin.StackedInline):
    ''' Keep candidate-submitted review explanations visible beside the interview that produced them. '''
    model = HumanReviewRequest
    extra = 0
    readonly_fields = ('explanation', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        ''' Preserve candidate ownership of review requests by blocking staff-created records in Django admin. '''
        return False

@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    ''' Give staff one read-only view of interview lifecycle, transcript evidence, evaluator assessments and review requests. '''
    list_display = ('id', 'user', 'status', 'result', 'started_at', 'ended_at')
    list_filter = ('status', 'result')
    search_fields = ('user__email', 'id')
    readonly_fields = ('id', 'user', 'confirm_transcript', 'status', 'result', 'created_at', 'started_at', 'ended_at')
    inlines = (ConversationTurnInline, EvaluationAnswerInline, HumanReviewRequestInline)

    def has_add_permission(self, request):
        ''' Keep interview sessions candidate-created by blocking manual creation in Django admin. '''
        return False

@admin.register(ConversationTurn)
class ConversationTurnAdmin(admin.ModelAdmin):
    ''' Let staff search persisted candidate and interviewer transcript evidence without editing it. '''
    list_display = ('interview', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('interview__user__email', 'text')
    readonly_fields = ('interview', 'role', 'text', 'created_at')

    def has_add_permission(self, request):
        ''' Block manual transcript creation so stored evidence comes only from live candidate and interviewer turns. '''
        return False

@admin.register(EvaluationAnswer)
class EvaluationAnswerAdmin(admin.ModelAdmin):
    ''' Let staff inspect stored per-criterion evaluator assessments without editing them. '''
    list_display = ('interview', 'question_index', 'created_at')
    search_fields = ('interview__user__email', 'question', 'answer')
    readonly_fields = ('interview', 'question_index', 'question', 'answer', 'created_at')

    def has_add_permission(self, request):
        ''' Block manual criterion creation so stored evaluation evidence comes only from the evaluator. '''
        return False

@admin.register(HumanReviewRequest)
class HumanReviewRequestAdmin(admin.ModelAdmin):
    ''' Let staff find candidate-requested human reviews by interview or candidate email address. '''
    list_display = ('interview', 'candidate_email', 'created_at')
    search_fields = ('interview__user__email', 'explanation')
    readonly_fields = ('interview', 'explanation', 'created_at')

    def candidate_email(self, obj):
        ''' Expose the candidate's email in review listings so staff can identify the account behind each request. '''
        return obj.interview.user.email

    def has_add_permission(self, request):
        ''' Keep human-review requests candidate-initiated by blocking manual creation in Django admin. '''
        return False

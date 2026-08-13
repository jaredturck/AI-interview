from django.contrib import admin

from interviews.models import CompanyDocument, ConversationTurn, EvaluationAnswer, HumanReviewRequest, InterviewSession, Job


class ConversationTurnInline(admin.TabularInline):
    model = ConversationTurn
    extra = 0
    readonly_fields = ("role", "text", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class EvaluationAnswerInline(admin.TabularInline):
    model = EvaluationAnswer
    extra = 0
    readonly_fields = ("question_index", "question", "answer", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class HumanReviewRequestInline(admin.StackedInline):
    model = HumanReviewRequest
    extra = 0
    readonly_fields = ("name", "email", "explanation", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "status", "result", "candidate_name", "started_at", "ended_at")
    list_filter = ("status", "result", "job")
    search_fields = ("candidate_name", "candidate_email", "id")
    readonly_fields = (
        "id",
        "job",
        "candidate_name",
        "candidate_email",
        "language",
        "confirm_transcript",
        "status",
        "result",
        "access_token_hash",
        "created_at",
        "started_at",
        "ended_at",
    )
    inlines = (ConversationTurnInline, EvaluationAnswerInline, HumanReviewRequestInline)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HumanReviewRequest)
class HumanReviewRequestAdmin(admin.ModelAdmin):
    list_display = ("interview", "name", "email", "created_at")
    search_fields = ("name", "email", "interview__id")
    readonly_fields = ("interview", "name", "email", "explanation", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Job)
admin.site.register(CompanyDocument)

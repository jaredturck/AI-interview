''' Provide the recruitment admin site, job workflow and read-only candidate interview evidence. '''

from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from interviews.models import ConversationTurn, EvaluationAnswer, HumanReviewRequest, InterviewSession, Job, JobApplication
from interviews.services.jobs import create_job_from_configuration

class RecruitmentAdminSite(admin.AdminSite):
    ''' Present Django administration as a focused internal recruitment console. '''
    site_header = _('AI Interview Administration')
    site_title = _('AI Interview Admin')
    index_title = _('Recruitment dashboard')
    index_template = 'admin/index.html'

    def get_urls(self):
        ''' Add the agreed staff-only job creation workflow beside normal Django admin routes. '''
        urls = super().get_urls()
        custom_urls = [path('jobs/create-from-configuration/', self.admin_view(self.create_job_view), name='create_job_from_configuration')]
        return custom_urls + urls

    def each_context(self, request):
        ''' Add recruitment counts used by the custom dashboard and navigation chrome. '''
        context = super().each_context(request)
        context['recruitment_stats'] = {
            'open_jobs': Job.objects.filter(status='open').count(),
            'applications': JobApplication.objects.count(),
            'interviews_pending': JobApplication.objects.filter(status='interview_pending').count(),
            'interviews_evaluating': JobApplication.objects.filter(status='evaluating').count(),
            'reviews_requested': HumanReviewRequest.objects.count(),
        }
        return context

    def create_job_view(self, request):
        ''' Confirm and execute creation of one open Job snapshot from the current configuration files. '''
        if request.method == 'POST':
            job, error = create_job_from_configuration()

            if error:
                messages.error(request, error)
            else:
                messages.success(request, _('Job "%(title)s" was created and opened for applications.') % {'title': job.title})
                return HttpResponseRedirect(reverse('admin:interviews_job_change', args=[job.id]))

        context = {
            **self.each_context(request),
            'title': _('Create job from configuration'),
            'opts': Job._meta,
        }
        return TemplateResponse(request, 'admin/interviews/create_job.html', context)

recruitment_admin_site = RecruitmentAdminSite(name='admin')

class ReadOnlyEvidenceAdmin(admin.ModelAdmin):
    ''' Prevent staff from creating or deleting records that represent candidate or model evidence. '''
    def has_add_permission(self, request):
        ''' Block manual evidence creation. '''
        return False

    def has_delete_permission(self, request, obj=None):
        ''' Block manual evidence deletion. '''
        return False

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

class JobAdmin(admin.ModelAdmin):
    ''' Let staff inspect immutable Job snapshots and explicitly open or close candidate applications. '''
    list_display = ('title', 'subtitle', 'status_badge', 'application_count', 'interview_count', 'opened_at', 'closed_at')
    list_filter = ('status', 'opened_at', 'closed_at')
    search_fields = ('title', 'subtitle', 'description')
    readonly_fields = ('id', 'title', 'subtitle', 'description', 'evaluation_questions', 'status', 'created_at', 'opened_at', 'closed_at')
    actions = ('open_jobs', 'close_jobs')

    def has_add_permission(self, request):
        ''' Route staff through Create job from configuration instead of manual snapshot entry. '''
        return False

    def has_delete_permission(self, request, obj=None):
        ''' Preserve historical recruitment configuration referenced by candidate applications. '''
        return False

    @admin.display(description=_('Status'), ordering='status')
    def status_badge(self, obj):
        ''' Render a semantic status badge that the custom admin stylesheet can distinguish visually. '''
        return format_html('<span class="status-badge status-{}">{}</span>', obj.status, obj.get_status_display())

    @admin.display(description=_('Applications'))
    def application_count(self, obj):
        ''' Show how many candidates applied to the vacancy. '''
        return obj.applications.count()

    @admin.display(description=_('Interviews'))
    def interview_count(self, obj):
        ''' Show how many applications have an interview record. '''
        return InterviewSession.objects.filter(application__job=obj).count()

    @admin.action(description=_('Open selected jobs'))
    def open_jobs(self, request, queryset):
        ''' Re-open selected historical vacancies without mutating their stored recruitment criteria. '''
        queryset.update(status='open', opened_at=timezone.now(), closed_at=None)

    @admin.action(description=_('Close selected jobs'))
    def close_jobs(self, request, queryset):
        ''' Stop new applications while preserving existing applications and interview evidence. '''
        queryset.update(status='closed', closed_at=timezone.now())

class JobApplicationAdmin(ReadOnlyEvidenceAdmin):
    ''' Give staff one coherent application listing linked to the candidate, vacancy and interview outcome. '''
    list_display = ('candidate_email', 'job', 'status_badge', 'applied_at', 'interview_status', 'result')
    list_filter = ('job', 'status', 'interview__status', 'interview__result')
    search_fields = ('user__email', 'job__title', 'job__subtitle', 'interview__id')
    readonly_fields = ('id', 'user', 'job', 'status', 'applied_at', 'interview_link')

    @admin.display(description=_('Candidate'), ordering='user__email')
    def candidate_email(self, obj):
        ''' Expose the candidate email directly in application listings. '''
        return obj.user.email

    @admin.display(description=_('Status'), ordering='status')
    def status_badge(self, obj):
        ''' Render the application workflow state as a semantic badge. '''
        return format_html('<span class="status-badge status-{}">{}</span>', obj.status, obj.get_status_display())

    @admin.display(description=_('Interview status'), ordering='interview__status')
    def interview_status(self, obj):
        ''' Show the linked interview lifecycle state without requiring staff to open the record. '''
        interview = getattr(obj, 'interview', None)
        return interview.get_status_display() if interview else _('Not started')

    @admin.display(description=_('Result'), ordering='interview__result')
    def result(self, obj):
        ''' Show the automated outcome when the linked interview has completed evaluation. '''
        interview = getattr(obj, 'interview', None)
        return interview.get_result_display() if interview else _('Pending')

    @admin.display(description=_('Interview'))
    def interview_link(self, obj):
        ''' Link staff directly from an application to its immutable interview evidence when present. '''
        interview = getattr(obj, 'interview', None)

        if not interview:
            return _('Not started')

        url = reverse('admin:interviews_interviewsession_change', args=[interview.id])
        return format_html('<a href="{}">{}</a>', url, interview.id)

class InterviewSessionAdmin(ReadOnlyEvidenceAdmin):
    ''' Give staff one read-only view of interview lifecycle, transcript evidence, evaluator assessments and review requests. '''
    list_display = ('id', 'candidate_email', 'job_title', 'status_badge', 'result', 'started_at', 'ended_at')
    list_filter = ('status', 'result', 'application__job')
    search_fields = ('application__user__email', 'application__job__title', 'id')
    readonly_fields = ('id', 'application', 'candidate_email', 'job_title', 'confirm_transcript', 'status', 'result',
        'created_at', 'started_at', 'ended_at')
    inlines = (ConversationTurnInline, EvaluationAnswerInline, HumanReviewRequestInline)

    @admin.display(description=_('Candidate'), ordering='application__user__email')
    def candidate_email(self, obj):
        ''' Expose the candidate email directly from the linked application. '''
        return obj.application.user.email

    @admin.display(description=_('Job'), ordering='application__job__title')
    def job_title(self, obj):
        ''' Expose the linked immutable Job title beside interview evidence. '''
        return obj.application.job.title

    @admin.display(description=_('Status'), ordering='status')
    def status_badge(self, obj):
        ''' Render interview lifecycle state as a semantic status badge. '''
        return format_html('<span class="status-badge status-{}">{}</span>', obj.status, obj.get_status_display())

class ConversationTurnAdmin(ReadOnlyEvidenceAdmin):
    ''' Let staff search persisted candidate and interviewer transcript evidence without editing it. '''
    list_display = ('interview', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('interview__application__user__email', 'interview__application__job__title', 'text')
    readonly_fields = ('interview', 'role', 'text', 'created_at')

class EvaluationAnswerAdmin(ReadOnlyEvidenceAdmin):
    ''' Let staff inspect stored per-criterion evaluator assessments without editing them. '''
    list_display = ('interview', 'question_index', 'created_at')
    search_fields = ('interview__application__user__email', 'interview__application__job__title', 'question', 'answer')
    readonly_fields = ('interview', 'question_index', 'question', 'answer', 'created_at')

class HumanReviewRequestAdmin(ReadOnlyEvidenceAdmin):
    ''' Let staff find candidate-requested human reviews by interview, vacancy or candidate email address. '''
    list_display = ('interview', 'candidate_email', 'job_title', 'created_at')
    search_fields = ('interview__application__user__email', 'interview__application__job__title', 'explanation')
    readonly_fields = ('interview', 'candidate_email', 'job_title', 'explanation', 'created_at')

    @admin.display(description=_('Candidate'), ordering='interview__application__user__email')
    def candidate_email(self, obj):
        ''' Expose the candidate email in review listings so staff can identify the account behind each request. '''
        return obj.interview.application.user.email

    @admin.display(description=_('Job'), ordering='interview__application__job__title')
    def job_title(self, obj):
        ''' Expose the vacancy associated with the requested human review. '''
        return obj.interview.application.job.title

recruitment_admin_site.register(Job, JobAdmin)
recruitment_admin_site.register(JobApplication, JobApplicationAdmin)
recruitment_admin_site.register(InterviewSession, InterviewSessionAdmin)
recruitment_admin_site.register(ConversationTurn, ConversationTurnAdmin)
recruitment_admin_site.register(EvaluationAnswer, EvaluationAnswerAdmin)
recruitment_admin_site.register(HumanReviewRequest, HumanReviewRequestAdmin)
recruitment_admin_site.register(User, UserAdmin)
recruitment_admin_site.register(Group, GroupAdmin)

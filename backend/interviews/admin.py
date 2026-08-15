''' Provide the recruitment admin site, editable job specifications and read-only candidate interview evidence. '''

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from interviews.models import ConversationTurn, EvaluationAnswer, HumanReviewRequest, InterviewSession, Job, JobApplication, non_empty_lines

class JobAdminForm(forms.ModelForm):
    ''' Present recruitment specifications as readable staff-authored text areas with criterion validation. '''
    class Meta:
        model = Job
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 18}),
            'essential_requirements': forms.Textarea(attrs={'rows': 10}),
            'verification_requirements': forms.Textarea(attrs={'rows': 7}),
            'evaluation_questions': forms.Textarea(attrs={'rows': 12}),
        }
        help_texts = {
            'description': _('Candidate-facing role description. Describe the real work, responsibilities, environment and relevant technologies or professional context.'),
            'essential_requirements': _('One interview-assessable hard requirement per line. Every requirement must be demonstrated for the candidate to progress.'),
            'verification_requirements': _('One externally verifiable requirement per line, such as professional registration. '
                'The interview records claims only; it does not verify credentials.'),
            'evaluation_questions': _('One broader evidence criterion per line. These guide the interviewer and final evaluation without acting as automatic hard gates.'),
        }

    def clean(self):
        ''' Require enough authored evidence criteria while allowing locked historical snapshots to change status. '''
        cleaned_data = super().clean()

        if 'description' in self.fields and not str(cleaned_data.get('description') or '').strip():
            self.add_error('description', _('Enter a job description.'))

        if 'essential_requirements' in self.fields and not non_empty_lines(str(cleaned_data.get('essential_requirements') or '')):
            self.add_error('essential_requirements', _('Enter at least one essential requirement.'))

        if 'evaluation_questions' in self.fields and not non_empty_lines(str(cleaned_data.get('evaluation_questions') or '')):
            self.add_error('evaluation_questions', _('Enter at least one evaluation criterion.'))

        return cleaned_data

class RecruitmentAdminSite(admin.AdminSite):
    ''' Present Django administration as a focused internal recruitment console. '''
    site_header = _('AI Interview Administration')
    site_title = _('AI Interview Admin')
    index_title = _('Recruitment dashboard')
    index_template = 'admin/index.html'
    enable_nav_sidebar = False

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
        context['admin_navigation'] = self.get_navigation(request, context.get('available_apps', []))
        return context

    def get_navigation(self, request, available_apps):
        ''' Build the compact permission-aware navigation used by the custom top bar. '''
        models = {}

        for app in available_apps:
            for model in app['models']:
                models[(app['app_label'], model['object_name'].lower())] = model

        groups = [
            {
                'label': _('Recruitment'),
                'items': [
                    {'label': _('Create job'), 'url': reverse('admin:interviews_job_add') if request.user.has_perm('interviews.add_job') else ''},
                    {'label': _('Jobs'), 'model': models.get(('interviews', 'job'))},
                    {'label': _('Job applications'), 'model': models.get(('interviews', 'jobapplication'))},
                ]
            },
            {
                'label': _('Interviews'),
                'items': [
                    {'label': _('Interview sessions'), 'model': models.get(('interviews', 'interviewsession'))},
                    {'label': _('Conversation turns'), 'model': models.get(('interviews', 'conversationturn'))},
                    {'label': _('Evaluation answers'), 'model': models.get(('interviews', 'evaluationanswer'))},
                    {'label': _('Human review requests'), 'model': models.get(('interviews', 'humanreviewrequest'))},
                ]
            },
            {
                'label': _('Access'),
                'items': [
                    {'label': _('Users'), 'model': models.get(('auth', 'user'))},
                    {'label': _('Groups'), 'model': models.get(('auth', 'group'))},
                ]
            },
        ]

        navigation = []

        for group in groups:
            items = []

            for item in group['items']:
                url = item.get('url')
                model = item.get('model')

                if model:
                    url = model.get('admin_url')

                if not url:
                    continue

                items.append({
                    'label': item['label'],
                    'url': url,
                    'active': request.path.startswith(url),
                })

            if items:
                navigation.append({
                    'label': group['label'],
                    'items': items,
                    'active': any(item['active'] for item in items),
                })

        return navigation

recruitment_admin_site = RecruitmentAdminSite(name='admin')

class ReadOnlyEvidenceAdmin(admin.ModelAdmin):
    ''' Prevent manual evidence creation while retaining normal Django delete permissions. '''
    def has_add_permission(self, request):
        ''' Block manual evidence creation. '''
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
    ''' Keep structured criterion assessments visible beside their interview without allowing staff to alter evaluator evidence. '''
    model = EvaluationAnswer
    extra = 0
    readonly_fields = ('question_index', 'criterion_type', 'question', 'assessment', 'answer', 'created_at')
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
    ''' Let staff author vacancies directly while locking recruitment specifications once applications exist. '''
    form = JobAdminForm
    list_display = ('title', 'sample_badge', 'status_badge', 'application_count', 'interview_count', 'opened_at', 'closed_at')
    list_filter = ('is_sample', 'status', 'opened_at', 'closed_at')
    search_fields = ('title', 'subtitle', 'description', 'essential_requirements', 'evaluation_questions')
    readonly_fields = ('id', 'is_sample', 'sample_key', 'created_at', 'opened_at', 'closed_at')
    actions = ('open_jobs', 'close_jobs')
    fieldsets = (
        (None, {'fields': ('id', 'title', 'subtitle', 'description')}),
        (_('Interview specification'), {'fields': ('essential_requirements', 'verification_requirements', 'evaluation_questions')}),
        (_('Vacancy state'), {'fields': ('status', 'is_sample', 'sample_key', 'created_at', 'opened_at', 'closed_at')}),
    )

    def get_readonly_fields(self, request, obj=None):
        ''' Freeze recruitment content after the first application while leaving vacancy status manageable. '''
        readonly = list(self.readonly_fields)

        if obj and obj.applications.exists():
            readonly.extend(['title', 'subtitle', 'description', 'essential_requirements', 'verification_requirements', 'evaluation_questions'])

        return readonly

    def save_model(self, request, obj, form, change):
        ''' Keep open/closed timestamps aligned when staff change vacancy status through the normal form. '''
        previous_status = Job.objects.filter(pk=obj.pk).values_list('status', flat=True).first() if change else None

        if obj.status == 'open' and previous_status != 'open':
            obj.opened_at = timezone.now()
            obj.closed_at = None
        elif obj.status == 'closed' and previous_status != 'closed':
            obj.closed_at = timezone.now()

        super().save_model(request, obj, form, change)

    @admin.display(description=_('Type'), ordering='is_sample')
    def sample_badge(self, obj):
        ''' Make seeded demonstration vacancies immediately distinguishable from normal recruitment data. '''
        label = _('Sample') if obj.is_sample else _('Normal')
        css_class = 'sample' if obj.is_sample else 'normal'
        return format_html('<span class="status-badge status-{}">{}</span>', css_class, label)

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
    ''' Let staff inspect structured per-criterion evaluator assessments without editing them. '''
    list_display = ('interview', 'question_index', 'criterion_type', 'assessment', 'created_at')
    list_filter = ('criterion_type', 'assessment')
    search_fields = ('interview__application__user__email', 'interview__application__job__title', 'question', 'answer')
    readonly_fields = ('interview', 'question_index', 'criterion_type', 'question', 'assessment', 'answer', 'created_at')

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

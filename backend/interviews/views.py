''' Expose session-authenticated candidate authentication, jobs, applications, interviews and human-review APIs. '''

import csv, json

from django.contrib.auth import authenticate, get_user_model, login as django_login, logout as django_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from interviews.models import ConversationTurn, HumanReviewRequest, InterviewSession, Job, JobApplication
from interviews.services.interview import INTERVIEW_MAX_MINUTES, interview_remaining_seconds
from interviews.services.runtime import model_runtime

RECRUITMENT_EMAIL = 'recruitment@example.com'
User = get_user_model()

def read_json(request):
    ''' Give API endpoints a consistent empty-payload and invalid-JSON fallback. '''
    if not request.body:
        return {}

    try:
        data = json.loads(request.body.decode('utf-8'))

    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}

def api_error(code, message, status):
    ''' Return one stable API error code with a localized human-readable fallback message. '''
    return JsonResponse({'error': message, 'code': code}, status=status)

def authentication_error():
    ''' Keep unauthenticated API responses consistent across protected endpoints. '''
    return api_error('authentication_required', _('Authentication is required.'), 401)

def recover_interrupted_evaluation(interview):
    ''' Convert stale evaluating state left by a backend restart into explicit evaluation_failed status. '''
    if interview.status == 'evaluating' and not model_runtime.evaluating:
        interview.status = 'evaluation_failed'
        interview.save(update_fields=['status'])
        interview.application.status = 'complete'
        interview.application.save(update_fields=['status'])

    return interview

def owned_application(request, application_id):
    ''' Enforce candidate ownership when resolving application IDs in HTTP endpoints. '''
    if not request.user.is_authenticated:
        return None

    return JobApplication.objects.select_related('job').filter(id=application_id, user=request.user).first()

def owned_interview(request, interview_id):
    ''' Enforce candidate ownership when resolving interview IDs in HTTP endpoints. '''
    if not request.user.is_authenticated:
        return None

    return InterviewSession.objects.select_related('application__job').filter(id=interview_id, application__user=request.user).first()

def serialize_job(job, application=None, include_description=False):
    ''' Shape one Job snapshot for candidate job listings and detail pages. '''
    data = {
        'id': str(job.id),
        'title': job.title,
        'subtitle': job.subtitle,
        'status': job.status,
        'opened_at': job.opened_at.isoformat() if job.opened_at else None,
        'application': serialize_application_summary(application) if application else None,
    }

    if include_description:
        data['description'] = job.description
    else:
        data['description_excerpt'] = job.description[:360]

    return data

def serialize_interview_summary(interview):
    ''' Shape one interview lifecycle summary for applications and account responses. '''
    if not interview:
        return None

    recover_interrupted_evaluation(interview)
    return {
        'id': str(interview.id),
        'status': interview.status,
        'result': interview.result,
        'created_at': interview.created_at.isoformat(),
        'started_at': interview.started_at.isoformat() if interview.started_at else None,
        'ended_at': interview.ended_at.isoformat() if interview.ended_at else None,
        'review_requested': hasattr(interview, 'review_request'),
    }

def serialize_application_summary(application):
    ''' Shape the application state needed beside a vacancy card or job detail. '''
    interview = getattr(application, 'interview', None)
    return {
        'id': str(application.id),
        'status': application.status,
        'applied_at': application.applied_at.isoformat(),
        'interview': serialize_interview_summary(interview),
    }

def serialize_application(application):
    ''' Shape a candidate-owned application together with its linked Job and interview state. '''
    data = serialize_application_summary(application)
    data['job'] = serialize_job(application.job, include_description=True)
    return data

@ensure_csrf_cookie
@require_GET
def auth_status(request):
    ''' Tell the frontend whether the Django session is authenticated while ensuring a CSRF cookie exists. '''
    if not request.user.is_authenticated:
        return JsonResponse({'authenticated': False})

    return JsonResponse({'authenticated': True, 'email': request.user.email})

@require_POST
def signup(request):
    ''' Create an email and password Django account and immediately establish the candidate's session. '''
    data = read_json(request)
    email = User.objects.normalize_email(data.get('email', '').strip().lower())
    password = data.get('password', '')

    if len(email) > User._meta.get_field('username').max_length:
        return api_error('email_too_long', _('The email address is too long.'), 400)

    try:
        validate_email(email)
        validate_password(password, user=User(username=email, email=email))

    except ValidationError as error:
        return api_error('invalid_credentials', error.messages[0], 400)

    if User.objects.filter(username=email).exists():
        return api_error('account_exists', _('An account with that email already exists.'), 409)

    try:
        user = User.objects.create_user(username=email, email=email, password=password)

    except IntegrityError:
        return api_error('account_exists', _('An account with that email already exists.'), 409)

    django_login(request, user)
    return JsonResponse({'authenticated': True, 'email': user.email}, status=201)

@require_POST
def login(request):
    ''' Authenticate a candidate's email and password into the Django session. '''
    data = read_json(request)
    email = User.objects.normalize_email(data.get('email', '').strip().lower())
    password = data.get('password', '')
    user = authenticate(request, username=email, password=password)

    if not user:
        return api_error('invalid_login', _('The email or password is incorrect.'), 401)

    django_login(request, user)
    return JsonResponse({'authenticated': True, 'email': user.email})

@require_POST
def logout(request):
    ''' End the candidate Django session and report unauthenticated state. '''
    django_logout(request)
    return JsonResponse({'authenticated': False})

@require_GET
def account(request):
    ''' Provide the candidate dashboard with application, job, interview outcome and review state. '''
    if not request.user.is_authenticated:
        return authentication_error()

    applications = JobApplication.objects.filter(user=request.user).select_related('job', 'interview', 'interview__review_request')
    return JsonResponse({'email': request.user.email, 'applications': [serialize_application(application) for application in applications]})

@require_GET
def download_interview_transcripts(request):
    ''' Download only this candidate's interview transcript turns and role context as CSV. '''
    if not request.user.is_authenticated:
        return authentication_error()

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="interview-transcripts.csv"'
    writer = csv.writer(response)
    writer.writerow(['job_title', 'job_subtitle', 'interview_date', 'speaker', 'turn_time', 'text'])
    turns = ConversationTurn.objects.filter(interview__application__user=request.user).select_related(
        'interview__application__job').order_by('interview__created_at', 'created_at', 'id')

    for turn in turns:
        interview = turn.interview
        job = interview.application.job
        speaker = 'candidate' if turn.role == 'user' else 'interviewer'
        writer.writerow([job.title, job.subtitle, interview.created_at.isoformat(), speaker, turn.created_at.isoformat(), turn.text])

    return response

@require_POST
def delete_interview_data(request, interview_id):
    ''' Permanently remove one candidate-owned application interview and every dependent evidence record. '''
    interview = owned_interview(request, interview_id)

    if not interview:
        return api_error('interview_not_found', _('Interview not found.'), 404)

    application = interview.application
    model_runtime.release_interview(interview.id)
    interview.delete()
    application.status = 'withdrawn'
    application.save(update_fields=['status'])
    return JsonResponse({'deleted': True, 'application_status': application.status})

@require_POST
def delete_all_interview_data(request):
    ''' Permanently remove every recruitment application and interview record while preserving the login account. '''
    if not request.user.is_authenticated:
        return authentication_error()

    interview_ids = InterviewSession.objects.filter(application__user=request.user).values_list('id', flat=True)

    for interview_id in interview_ids:
        model_runtime.release_interview(interview_id)

    JobApplication.objects.filter(user=request.user).delete()
    return JsonResponse({'deleted': True})

@ensure_csrf_cookie
@require_GET
def bootstrap(request):
    ''' Provide public UI metadata that is genuinely global rather than tied to one vacancy. '''
    return JsonResponse({'max_minutes': INTERVIEW_MAX_MINUTES, 'recruitment_email': RECRUITMENT_EMAIL})

@require_GET
def jobs(request):
    ''' List open vacancies and annotate each one with this candidate's existing application state. '''
    if not request.user.is_authenticated:
        return authentication_error()

    open_jobs = list(Job.objects.filter(status='open'))
    applications = JobApplication.objects.filter(user=request.user, job_id__in=[job.id for job in open_jobs]).select_related(
        'interview', 'interview__review_request')
    application_map = {application.job_id: application for application in applications}
    return JsonResponse({'jobs': [serialize_job(job, application_map.get(job.id)) for job in open_jobs]})

@require_GET
def job_detail(request, job_id):
    ''' Return one open vacancy or a closed vacancy that the current candidate already applied for. '''
    if not request.user.is_authenticated:
        return authentication_error()

    application = JobApplication.objects.filter(user=request.user, job_id=job_id).select_related('interview', 'interview__review_request').first()
    job = Job.objects.filter(id=job_id).first()

    if not job or job.status != 'open' and not application:
        return api_error('job_not_found', _('Job not found.'), 404)

    return JsonResponse({'job': serialize_job(job, application, include_description=True)})

@require_POST
def apply_job(request, job_id):
    ''' Create at most one candidate application for an open vacancy. '''
    if not request.user.is_authenticated:
        return authentication_error()

    job = Job.objects.filter(id=job_id).first()

    if not job:
        return api_error('job_not_found', _('Job not found.'), 404)

    if job.status != 'open':
        return api_error('job_closed', _('This job is no longer open for applications.'), 409)

    try:
        application, created = JobApplication.objects.get_or_create(user=request.user, job=job)

    except IntegrityError:
        application = JobApplication.objects.get(user=request.user, job=job)
        created = False

    status = 201 if created else 200
    return JsonResponse({'application': serialize_application(application)}, status=status)

@require_GET
def application_detail(request, application_id):
    ''' Return one candidate-owned application with its Job snapshot and interview state. '''
    application = owned_application(request, application_id)

    if not application:
        return api_error('application_not_found', _('Application not found.'), 404)

    application = JobApplication.objects.select_related('job', 'interview', 'interview__review_request').get(id=application.id)
    return JsonResponse({'application': serialize_application(application)})

@require_POST
def start_application_interview(request, application_id):
    ''' Resume an application's existing interview or create one when the realtime worker is available. '''
    application = owned_application(request, application_id)

    if not application:
        return api_error('application_not_found', _('Application not found.'), 404)

    if application.status == 'withdrawn':
        return api_error('application_withdrawn', _('This application has been withdrawn.'), 409)

    existing = getattr(application, 'interview', None)

    if existing:
        return JsonResponse({'interview': serialize_interview_summary(existing), 'job': serialize_job(application.job)})

    if not model_runtime.capacity_available():
        return api_error('worker_busy', _('The interview worker is currently busy. Please try again shortly.'), 503)

    data = read_json(request)
    interview, created = InterviewSession.objects.get_or_create(application=application,
        defaults={'confirm_transcript': bool(data.get('confirm_transcript', False))})
    application.status = 'interview_in_progress'
    application.save(update_fields=['status'])
    status = 201 if created else 200
    return JsonResponse({'interview': serialize_interview_summary(interview), 'job': serialize_job(application.job)}, status=status)

@require_GET
def interview_status(request, interview_id):
    ''' Provide polling and reconnect state for one candidate-owned interview and its automated outcome. '''
    interview = owned_interview(request, interview_id)

    if not interview:
        return api_error('interview_not_found', _('Interview not found.'), 404)

    recover_interrupted_evaluation(interview)
    return JsonResponse({
        'interview': serialize_interview_summary(interview),
        'application': {'id': str(interview.application.id), 'status': interview.application.status},
        'job': serialize_job(interview.application.job),
        'max_minutes': INTERVIEW_MAX_MINUTES,
        'remaining_seconds': interview_remaining_seconds(interview) if interview.started_at else None,
    })

@require_POST
def request_review(request, interview_id):
    ''' Record the candidate's explanation for human review after automated evaluation finishes or fails. '''
    interview = owned_interview(request, interview_id)

    if not interview:
        return api_error('interview_not_found', _('Interview not found.'), 404)

    if interview.status not in ['evaluated', 'evaluation_failed']:
        return api_error('review_not_available', _('Human review can be requested after automated processing is complete.'), 409)

    explanation = read_json(request).get('explanation', '').strip()[:10000]

    if not explanation:
        return api_error('review_explanation_required', _('Please explain what you would like reviewed.'), 400)

    review, created = HumanReviewRequest.objects.get_or_create(interview=interview, defaults={'explanation': explanation})
    status = 201 if created else 200
    return JsonResponse({'review_id': review.id, 'submitted': True}, status=status)

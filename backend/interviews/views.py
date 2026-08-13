''' Expose session-authenticated candidate account, interview, status and human-review APIs. '''

import json

from django.contrib.auth import authenticate, get_user_model, login as django_login, logout as django_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from interviews.models import HumanReviewRequest, InterviewSession
from interviews.services.content import get_job_title
from interviews.services.interview import INTERVIEW_MAX_MINUTES
from interviews.services.runtime import model_runtime

RECRUITMENT_EMAIL = 'recruitment@example.com'
User = get_user_model()

def read_json(request):
    ''' Give API endpoints a consistent empty-payload and invalid-JSON fallback. '''
    if not request.body:
        return {}

    try:
        return json.loads(request.body.decode('utf-8'))

    except json.JSONDecodeError:
        return {}

def authentication_error():
    ''' Keep unauthenticated API responses consistent across protected endpoints. '''
    return JsonResponse({'error': 'Authentication is required.'}, status=401)

def recover_interrupted_evaluation(interview):
    ''' Convert stale evaluating state left by a backend restart into explicit evaluation_failed status. '''
    if interview.status == 'evaluating' and not model_runtime.evaluating:
        interview.status = 'evaluation_failed'
        interview.save(update_fields=['status'])

    return interview

def owned_interview(request, interview_id):
    ''' Enforce candidate ownership when resolving interview IDs in HTTP endpoints. '''
    if not request.user.is_authenticated:
        return None

    return InterviewSession.objects.filter(id=interview_id, user=request.user).first()

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
        return JsonResponse({'error': 'The email address is too long.'}, status=400)

    try:
        validate_email(email)
        validate_password(password, user=User(username=email, email=email))

    except ValidationError as error:
        return JsonResponse({'error': error.messages[0]}, status=400)

    if User.objects.filter(username=email).exists():
        return JsonResponse({'error': 'An account with that email already exists.'}, status=409)

    try:
        user = User.objects.create_user(username=email, email=email, password=password)

    except IntegrityError:
        return JsonResponse({'error': 'An account with that email already exists.'}, status=409)

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
        return JsonResponse({'error': 'The email or password is incorrect.'}, status=401)

    django_login(request, user)
    return JsonResponse({'authenticated': True, 'email': user.email})

@require_POST
def logout(request):
    ''' End the candidate Django session and report unauthenticated state. '''
    django_logout(request)
    return JsonResponse({'authenticated': False})

@require_GET
def account(request):
    ''' Provide the account screen with candidate identity, interview history, outcomes and review status. '''
    if not request.user.is_authenticated:
        return authentication_error()

    interviews = []

    for interview in request.user.interviews.select_related('review_request').order_by('-created_at'):
        recover_interrupted_evaluation(interview)
        interviews.append({
            'id': str(interview.id),
            'status': interview.status,
            'result': interview.result,
            'created_at': interview.created_at.isoformat(),
            'ended_at': interview.ended_at.isoformat() if interview.ended_at else None,
            'review_requested': hasattr(interview, 'review_request')
        })

    return JsonResponse({'email': request.user.email, 'interviews': interviews})

@ensure_csrf_cookie
@require_GET
def bootstrap(request):
    ''' Provide public interview UI metadata without requiring an authenticated session. '''
    return JsonResponse({
        'job': {'title': get_job_title()},
        'max_minutes': INTERVIEW_MAX_MINUTES,
        'recruitment_email': RECRUITMENT_EMAIL,
    })

@require_POST
def start_interview(request):
    ''' Resume the candidate's unfinished interview or create one only when the realtime worker is available. '''
    if not request.user.is_authenticated:
        return authentication_error()

    existing = request.user.interviews.filter(status__in=['created', 'active']).order_by('-created_at').first()

    if existing:
        return JsonResponse({'interview_id': str(existing.id), 'job_title': get_job_title()})

    if not model_runtime.capacity_available():
        return JsonResponse({'error': 'The interview worker is currently busy. Please try again shortly.'}, status=503)

    data = read_json(request)
    interview = InterviewSession.objects.create(user=request.user, confirm_transcript=bool(data.get('confirm_transcript', False)))
    return JsonResponse({'interview_id': str(interview.id), 'job_title': get_job_title()}, status=201)

@require_GET
def interview_status(request, interview_id):
    ''' Provide polling and reconnect state for one candidate-owned interview and its automated outcome. '''
    interview = owned_interview(request, interview_id)

    if not interview:
        return JsonResponse({'error': 'Interview not found.'}, status=404)

    recover_interrupted_evaluation(interview)
    return JsonResponse({
        'status': interview.status,
        'result': interview.result,
        'ended_at': interview.ended_at.isoformat() if interview.ended_at else None,
        'review_requested': hasattr(interview, 'review_request'),
    })

@require_POST
def request_review(request, interview_id):
    ''' Record the candidate's explanation for human review after automated evaluation finishes or fails. '''
    interview = owned_interview(request, interview_id)

    if not interview:
        return JsonResponse({'error': 'Interview not found.'}, status=404)

    if interview.status not in ['evaluated', 'evaluation_failed']:
        return JsonResponse({'error': 'Human review can be requested after automated processing is complete.'}, status=409)

    explanation = read_json(request).get('explanation', '').strip()[:10000]

    if not explanation:
        return JsonResponse({'error': 'Please explain what you would like reviewed.'}, status=400)

    review, created = HumanReviewRequest.objects.get_or_create(interview=interview, defaults={'explanation': explanation})

    if not created:
        return JsonResponse({'review_id': review.id, 'submitted': True})

    return JsonResponse({'review_id': review.id, 'submitted': True}, status=201)

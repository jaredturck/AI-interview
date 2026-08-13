''' HTTP endpoints for interview setup, status and candidate review requests. '''
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from ai_interviewer.runtime_config import RUNTIME
from interviews.models import HumanReviewRequest, InterviewSession
from interviews.services.content import get_job_title
from interviews.services.runtime import model_runtime

SUPPORTED_LANGUAGES = [
    'English', 'Chinese', 'Japanese', 'Korean', 'German', 'French', 'Russian', 'Portuguese', 'Spanish', 'Italian'
]

def read_json(request):
    ''' Decode a JSON request body or return an empty dictionary. '''
    if not request.body:
        return {}

    try:
        return json.loads(request.body.decode('utf-8'))

    except json.JSONDecodeError:
        return {}

def token_from_request(request):
    ''' Return the interview access token supplied by the browser. '''
    return request.headers.get('X-Interview-Token', '')

def authorized_interview(request, interview_id):
    ''' Return an interview when the request carries its matching token. '''
    interview = get_object_or_404(InterviewSession, id=interview_id)
    token = token_from_request(request)

    if not token or not interview.token_matches(token):
        return None

    return interview

@ensure_csrf_cookie
@require_GET
def bootstrap(request):
    ''' Return public setup information required by the interview screen. '''
    return JsonResponse({
        'job': {'title': get_job_title()},
        'languages': SUPPORTED_LANGUAGES,
        'review_transcript_default': RUNTIME['interview']['review_transcript_default'],
        'max_minutes': RUNTIME['interview']['max_minutes'],
        'capacity_available': model_runtime.capacity_available(),
        'recruitment_email': RUNTIME['company']['recruitment_email'],
    })

@require_POST
def start_interview(request):
    ''' Create a candidate interview session and issue its browser token. '''
    if not model_runtime.capacity_available():
        return JsonResponse({'error': 'The interview worker is currently busy. Please try again shortly.'}, status=503)

    data = read_json(request)
    language = data.get('language', 'English')

    if language not in SUPPORTED_LANGUAGES:
        language = 'English'

    interview = InterviewSession(
        candidate_name=data.get('name', '')[:200],
        candidate_email=data.get('email', '')[:254],
        language=language,
        confirm_transcript=bool(data.get('confirm_transcript', False)),
        status='created',
    )
    token = interview.issue_access_token()
    interview.save()

    return JsonResponse({
        'interview_id': str(interview.id),
        'access_token': token,
        'job_title': get_job_title(),
        'language': interview.language,
    }, status=201)

@require_GET
def interview_status(request, interview_id):
    ''' Return the current automated interview and evaluation status. '''
    interview = authorized_interview(request, interview_id)

    if not interview:
        return JsonResponse({'error': 'Not authorized.'}, status=403)

    return JsonResponse({
        'status': interview.status,
        'result': interview.result,
        'ended_at': interview.ended_at.isoformat() if interview.ended_at else None,
        'review_requested': interview.review_requests.exists(),
    })

@require_POST
def request_review(request, interview_id):
    ''' Store a candidate-requested human review after automated processing. '''
    interview = authorized_interview(request, interview_id)

    if not interview:
        return JsonResponse({'error': 'Not authorized.'}, status=403)

    if interview.status not in ['evaluated', 'evaluation_failed']:
        return JsonResponse({'error': 'Human review can be requested after automated processing is complete.'}, status=409)

    data = read_json(request)
    name = data.get('name', '').strip()[:200]
    email = data.get('email', '').strip()[:254]
    explanation = data.get('explanation', '').strip()[:10000]

    if not name or not email or not explanation:
        return JsonResponse({'error': 'Name, email and explanation are required.'}, status=400)

    existing = interview.review_requests.order_by('created_at').first()

    if existing:
        return JsonResponse({'review_id': existing.id, 'submitted': True})

    review = HumanReviewRequest.objects.create(interview=interview, name=name, email=email, explanation=explanation)
    return JsonResponse({'review_id': review.id, 'submitted': True}, status=201)

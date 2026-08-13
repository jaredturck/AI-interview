import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from ai_interviewer.runtime_config import RUNTIME
from interviews.models import HumanReviewRequest, InterviewSession, Job
from interviews.services.runtime import model_runtime

SUPPORTED_LANGUAGES = [
    "English",
    "Chinese",
    "Japanese",
    "Korean",
    "German",
    "French",
    "Russian",
    "Portuguese",
    "Spanish",
    "Italian",
]


def read_json(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def token_from_request(request):
    return request.headers.get("X-Interview-Token", "")


def authorized_interview(request, interview_id):
    interview = get_object_or_404(InterviewSession.objects.select_related("job"), id=interview_id)
    token = token_from_request(request)
    if not token or not interview.token_matches(token):
        return None
    return interview


@ensure_csrf_cookie
@require_GET
def bootstrap(request):
    job = Job.objects.filter(is_active=True).first()
    return JsonResponse({
        "job": {"id": job.id, "title": job.title} if job else None,
        "languages": SUPPORTED_LANGUAGES,
        "review_transcript_default": RUNTIME["interview"]["review_transcript_default"],
        "max_minutes": RUNTIME["interview"]["max_minutes"],
        "capacity_available": model_runtime.capacity_available(),
        "recruitment_email": RUNTIME["company"]["recruitment_email"],
    })


@require_POST
def start_interview(request):
    if not model_runtime.capacity_available():
        return JsonResponse({"error": "The interview worker is currently busy. Please try again shortly."}, status=503)

    data = read_json(request)
    job = Job.objects.filter(id=data.get("job_id"), is_active=True).first()
    if not job:
        return JsonResponse({"error": "No active job is available."}, status=404)

    language = data.get("language", "English")
    if language not in SUPPORTED_LANGUAGES:
        language = "English"

    interview = InterviewSession(
        job=job,
        candidate_name=data.get("name", "")[:200],
        candidate_email=data.get("email", "")[:254],
        language=language,
        confirm_transcript=bool(data.get("confirm_transcript", False)),
        status="created",
    )
    token = interview.issue_access_token()
    interview.save()

    return JsonResponse({
        "interview_id": str(interview.id),
        "access_token": token,
        "job_title": job.title,
        "language": interview.language,
    }, status=201)


@require_GET
def interview_status(request, interview_id):
    interview = authorized_interview(request, interview_id)
    if not interview:
        return JsonResponse({"error": "Not authorized."}, status=403)

    return JsonResponse({
        "status": interview.status,
        "result": interview.result,
        "ended_at": interview.ended_at.isoformat() if interview.ended_at else None,
        "review_requested": interview.review_requests.exists(),
    })


@require_POST
def request_review(request, interview_id):
    interview = authorized_interview(request, interview_id)
    if not interview:
        return JsonResponse({"error": "Not authorized."}, status=403)

    data = read_json(request)
    name = data.get("name", "").strip()[:200]
    email = data.get("email", "").strip()[:254]
    explanation = data.get("explanation", "").strip()[:10000]

    if not name or not email or not explanation:
        return JsonResponse({"error": "Name, email and explanation are required."}, status=400)

    existing = interview.review_requests.order_by("created_at").first()
    if existing:
        return JsonResponse({"review_id": existing.id, "submitted": True}, status=200)

    review = HumanReviewRequest.objects.create(
        interview=interview,
        name=name,
        email=email,
        explanation=explanation,
    )
    return JsonResponse({"review_id": review.id, "submitted": True}, status=201)

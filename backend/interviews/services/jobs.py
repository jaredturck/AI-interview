''' Create immutable Job snapshots from staff-authored configuration and concise Qwen metadata. '''

import json, re

from django.utils import timezone
from django.utils.translation import gettext as _

from interviews.models import Job
from interviews.services.content import get_job_configuration, parse_evaluation_questions
from interviews.services.runtime import model_runtime

def parse_job_metadata(text):
    ''' Parse the title and optional subtitle from the compact JSON returned by Qwen. '''
    match = re.search(r'\{.*\}', text, flags=re.DOTALL)

    if not match:
        return None

    try:
        data = json.loads(match.group(0))

    except json.JSONDecodeError:
        return None

    title = str(data.get('title') or '').strip()[:120]
    subtitle = str(data.get('subtitle') or '').strip()[:160]

    if not title:
        return None

    return {'title': title, 'subtitle': subtitle}

def create_job_from_configuration():
    ''' Snapshot the current recruitment files, derive display metadata once and open the resulting vacancy. '''
    description, evaluation_questions = get_job_configuration()

    if not description:
        return None, _('The configured job description is empty.')

    if not parse_evaluation_questions(evaluation_questions):
        return None, _('The configured evaluation questions are empty.')

    try:
        metadata_text = model_runtime.generate_job_metadata(description)

    except Exception:  # noqa: BLE001
        return None, _('The AI model could not derive job metadata. Please try again when the interview worker is available.')

    if not metadata_text:
        return None, _('The AI model could not derive job metadata. Please try again when the interview worker is available.')

    metadata = parse_job_metadata(metadata_text)

    if not metadata:
        return None, _('The AI model returned invalid job metadata. No job was created.')

    job = Job.objects.create(title=metadata['title'], subtitle=metadata['subtitle'], description=description,
        evaluation_questions=evaluation_questions, status='open', opened_at=timezone.now())
    return job, ''

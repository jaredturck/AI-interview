import pytest
from channels.testing import WebsocketCommunicator
from ai_interviewer.asgi import application
from interviews.models import InterviewSession, Job
from interviews.services.runtime import model_runtime


def no_evaluation(interview_id):
    return None


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_typed_websocket_turn(monkeypatch):
    job = await Job.objects.acreate(
        title="Backend Developer",
        description="Python and SQL backend development.",
        evaluation_questions=["Programming ability?"],
    )
    interview = InterviewSession(job=job, status="created", language="English")
    token = interview.issue_access_token()
    await interview.asave()
    model_runtime.active_interview_id = None
    monkeypatch.setattr("interviews.consumers.start_evaluation", no_evaluation)

    communicator = WebsocketCommunicator(application, f"/ws/interviews/{interview.id}/", headers=[(b"origin", b"http://localhost")])
    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_json_to({"type": "auth", "token": token})
    ready = await communicator.receive_json_from()
    assert ready["type"] == "ready"
    await interview.arefresh_from_db()
    assert interview.status == "active"

    status = await communicator.receive_json_from()
    assert status["type"] == "status"
    assistant = await communicator.receive_json_from()
    assert assistant["type"] == "assistant"

    speaking = await communicator.receive_json_from()
    assert speaking == {"type": "status", "status": "speaking"}
    audio = await communicator.receive_json_from()
    assert audio["type"] == "audio"
    ready_after_opening = await communicator.receive_json_from()
    assert ready_after_opening == {"type": "status", "status": "ready"}

    await communicator.send_json_to({"type": "text", "text": "I built a Django API with PostgreSQL."})
    candidate = await communicator.receive_json_from()
    assert candidate == {"type": "candidate", "text": "I built a Django API with PostgreSQL."}

    await communicator.send_json_to({"type": "control", "action": "end"})
    seen_ended = False
    for _ in range(12):
        message = await communicator.receive_json_from()
        if message.get("type") == "ended":
            seen_ended = True
            break
    assert seen_ended is True
    await communicator.disconnect()
    model_runtime.release_interview(interview.id)

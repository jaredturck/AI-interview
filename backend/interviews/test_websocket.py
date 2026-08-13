''' Verify authenticated Django Channels interview flow and cross-account ownership isolation. '''

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import Client

from ai_interviewer.asgi import application
from interviews.models import InterviewSession

User = get_user_model()

def no_evaluation(interview_id):
    ''' Suppress background evaluation so WebSocket tests can assert the live-session handoff deterministically. '''
    return None

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_typed_websocket_turn(monkeypatch):
    ''' Verify an authenticated typed interview follows the live WebSocket protocol through completion. '''
    user = await sync_to_async(User.objects.create_user)(username='candidate@example.com', email='candidate@example.com', password='A-strong-test-password-42')
    interview = await InterviewSession.objects.acreate(user=user, status='created')
    client = Client()
    await sync_to_async(client.force_login)(user)
    session_cookie = client.cookies['sessionid'].value
    monkeypatch.setattr('interviews.consumers.start_evaluation', no_evaluation)

    headers = [(b'origin', b'http://localhost'), (b'cookie', f'sessionid={session_cookie}'.encode())]
    communicator = WebsocketCommunicator(application, f'/ws/interviews/{interview.id}/', headers=headers)
    connected, _ = await communicator.connect()
    assert connected is True

    loading = await communicator.receive_json_from()
    assert loading == {'type': 'status', 'status': 'loading'}
    history = await communicator.receive_json_from()
    assert history == {'type': 'history', 'turns': []}
    thinking = await communicator.receive_json_from()
    assert thinking == {'type': 'status', 'status': 'thinking'}
    assistant = await communicator.receive_json_from()
    assert assistant['type'] == 'assistant'
    speaking = await communicator.receive_json_from()
    assert speaking == {'type': 'status', 'status': 'speaking'}
    audio = await communicator.receive_from()
    assert isinstance(audio, bytes)
    ready = await communicator.receive_json_from()
    assert ready == {'type': 'ready'}

    candidate_text = 'I built a Django API with PostgreSQL.'
    await communicator.send_json_to({'type': 'text', 'text': candidate_text})
    candidate = await communicator.receive_json_from()
    assert candidate == {'type': 'candidate', 'text': candidate_text}

    await communicator.send_json_to({'type': 'control', 'action': 'end'})
    seen_ended = False

    for _ in range(12):
        message = await communicator.receive_from()

        if isinstance(message, str) and '"type": "ended"' in message:
            seen_ended = True
            break

    assert seen_ended is True
    await communicator.disconnect()

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_rejects_another_candidate():
    ''' Verify WebSocket ownership checks reject a different candidate before connection acceptance. '''
    owner = await sync_to_async(User.objects.create_user)(username='owner@example.com', email='owner@example.com', password='A-strong-test-password-42')
    other = await sync_to_async(User.objects.create_user)(username='other@example.com', email='other@example.com', password='A-strong-test-password-42')
    interview = await InterviewSession.objects.acreate(user=owner)
    client = Client()
    await sync_to_async(client.force_login)(other)
    session_cookie = client.cookies['sessionid'].value
    headers = [(b'origin', b'http://localhost'), (b'cookie', f'sessionid={session_cookie}'.encode())]
    communicator = WebsocketCommunicator(application, f'/ws/interviews/{interview.id}/', headers=headers)
    connected, close_code = await communicator.connect()
    assert connected is False
    assert close_code == 4404

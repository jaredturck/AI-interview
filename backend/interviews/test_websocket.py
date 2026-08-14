''' Verify authenticated Django Channels interview flow and cross-account ownership isolation. '''

import numpy as np
import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import Client

from ai_interviewer.asgi import application
from interviews.models import InterviewSession, Job, JobApplication
from interviews.services.runtime import model_runtime

User = get_user_model()

def no_evaluation(interview_id):
    ''' Suppress background evaluation so WebSocket tests can assert the live-session handoff deterministically. '''
    return None

async def create_interview(user):
    ''' Create a Job, candidate application and interview without crossing async ORM boundaries in each test. '''
    job = await Job.objects.acreate(title='Commercial Cleaner', description='Clean commercial facilities.', evaluation_questions='Reliability evidence')
    application = await JobApplication.objects.acreate(user=user, job=job)
    return await InterviewSession.objects.acreate(application=application, status='created')

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_typed_websocket_turn(monkeypatch):
    ''' Verify an authenticated typed interview follows the live WebSocket protocol through completion. '''
    user = await sync_to_async(User.objects.create_user)(username='candidate@example.com', email='candidate@example.com',
        password='A-strong-test-password-42')
    interview = await create_interview(user)
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

    candidate_text = 'I managed commercial cleaning schedules and quality checks.'
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
    interview = await create_interview(owner)
    client = Client()
    await sync_to_async(client.force_login)(other)
    session_cookie = client.cookies['sessionid'].value
    headers = [(b'origin', b'http://localhost'), (b'cookie', f'sessionid={session_cookie}'.encode())]
    communicator = WebsocketCommunicator(application, f'/ws/interviews/{interview.id}/', headers=headers)
    connected, close_code = await communicator.connect()
    assert connected is False
    assert close_code == 4404

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_ignores_non_speech_audio(monkeypatch):
    ''' Verify non-speech browser audio never becomes a candidate transcript turn. '''
    user = await sync_to_async(User.objects.create_user)(username='noise@example.com', email='noise@example.com', password='A-strong-test-password-42')
    interview = await create_interview(user)
    client = Client()
    await sync_to_async(client.force_login)(user)
    session_cookie = client.cookies['sessionid'].value
    monkeypatch.setattr('interviews.consumers.decode_browser_audio', lambda audio_bytes: (np.ones(1600, dtype=np.float32), 16000))
    monkeypatch.setattr(model_runtime.suite, 'has_speech', lambda audio, sample_rate: False)

    headers = [(b'origin', b'http://localhost'), (b'cookie', f'sessionid={session_cookie}'.encode())]
    communicator = WebsocketCommunicator(application, f'/ws/interviews/{interview.id}/', headers=headers)
    connected, _ = await communicator.connect()
    assert connected is True

    for _ in range(7):
        await communicator.receive_from()

    await communicator.send_to(bytes_data=b'noise')
    ignored = await communicator.receive_json_from()
    ready = await communicator.receive_json_from()
    assert ignored == {'type': 'audio_ignored', 'pending_turn': False}
    assert ready == {'type': 'status', 'status': 'ready'}
    assert await communicator.receive_nothing(timeout=0.05) is True
    await communicator.disconnect()

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_accumulates_incomplete_speech_until_turn_completion(monkeypatch):
    ''' Verify a pause can hold the floor and resumed speech joins the same candidate turn before ASR. '''
    user = await sync_to_async(User.objects.create_user)(username='pause@example.com', email='pause@example.com', password='A-strong-test-password-42')
    interview = await create_interview(user)
    client = Client()
    await sync_to_async(client.force_login)(user)
    session_cookie = client.cookies['sessionid'].value
    monkeypatch.setattr('interviews.consumers.decode_browser_audio', lambda audio_bytes: (np.ones(1600, dtype=np.float32), 16000))
    monkeypatch.setattr('interviews.consumers.TURN_HOLD_SECONDS', 60)
    monkeypatch.setattr('interviews.consumers.TURN_COMPLETE_GRACE_SECONDS', 0)
    monkeypatch.setattr(model_runtime.suite, 'turn_complete', lambda audio, sample_rate: audio.size > 1600)

    headers = [(b'origin', b'http://localhost'), (b'cookie', f'sessionid={session_cookie}'.encode())]
    communicator = WebsocketCommunicator(application, f'/ws/interviews/{interview.id}/', headers=headers)
    connected, _ = await communicator.connect()
    assert connected is True

    for _ in range(7):
        await communicator.receive_from()

    await communicator.send_to(bytes_data=b'first-segment')
    assert await communicator.receive_json_from() == {'type': 'turn_pending'}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'listening'}

    await communicator.send_json_to({'type': 'speech_resumed'})
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'listening'}
    await communicator.send_to(bytes_data=b'second-segment')
    assert await communicator.receive_json_from() == {'type': 'turn_pending'}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'listening'}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'transcribing'}

    candidate = await communicator.receive_json_from()
    assert candidate == {'type': 'candidate', 'text': 'I managed commercial cleaning schedules and quality checks.'}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'thinking'}
    assert (await communicator.receive_json_from())['type'] == 'assistant'
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'speaking'}
    assert isinstance(await communicator.receive_from(), bytes)
    assert await communicator.receive_json_from() == {'type': 'ready'}
    await communicator.disconnect()

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_push_to_talk_submits_speech_without_smart_turn_wait(monkeypatch):
    ''' Verify closed-microphone push-to-talk keeps its explicit submit contract while still requiring speech. '''
    user = await sync_to_async(User.objects.create_user)(username='manual@example.com', email='manual@example.com', password='A-strong-test-password-42')
    interview = await create_interview(user)
    client = Client()
    await sync_to_async(client.force_login)(user)
    session_cookie = client.cookies['sessionid'].value
    monkeypatch.setattr('interviews.consumers.decode_browser_audio', lambda audio_bytes: (np.ones(1600, dtype=np.float32), 16000))
    monkeypatch.setattr(model_runtime.suite, 'turn_complete', lambda audio, sample_rate: False)

    headers = [(b'origin', b'http://localhost'), (b'cookie', f'sessionid={session_cookie}'.encode())]
    communicator = WebsocketCommunicator(application, f'/ws/interviews/{interview.id}/', headers=headers)
    connected, _ = await communicator.connect()
    assert connected is True

    for _ in range(7):
        await communicator.receive_from()

    await communicator.send_json_to({'type': 'audio_mode', 'manual': True})
    await communicator.send_to(bytes_data=b'push-to-talk')
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'transcribing'}
    assert await communicator.receive_json_from() == {
        'type': 'candidate',
        'text': 'I managed commercial cleaning schedules and quality checks.'
    }
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'thinking'}
    assert (await communicator.receive_json_from())['type'] == 'assistant'
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'speaking'}
    assert isinstance(await communicator.receive_from(), bytes)
    assert await communicator.receive_json_from() == {'type': 'ready'}
    await communicator.disconnect()

''' Verify authenticated Django Channels interview flow and cross-account ownership isolation. '''

from unittest.mock import Mock

import numpy as np
import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import Client

from ai_interviewer.asgi import application
from interviews.consumers import AUDIO_CHUNK_BYTES
from interviews.models import InterviewSession, Job, JobApplication
from interviews.services.interview import INTERVIEW_MAX_MINUTES, INTERVIEW_WRAP_UP_MINUTES
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

async def receive_audio_transfer(communicator):
    ''' Receive one chunked interviewer WAV and verify its framing and per-message bound. '''
    start = await communicator.receive_json_from()
    assert start['type'] == 'audio_start'
    chunks = []

    for _ in range(start['chunks']):
        chunk = await communicator.receive_from()
        assert isinstance(chunk, bytes)
        assert len(chunk) <= AUDIO_CHUNK_BYTES
        chunks.append(chunk)

    end = await communicator.receive_json_from()
    assert end == {'type': 'audio_end', 'id': start['id']}
    assert sum(len(chunk) for chunk in chunks) == start['bytes']
    return b''.join(chunks), chunks, start

async def send_candidate_audio_transfer(communicator, audio, manual=False):
    ''' Send one browser recording using the same bounded transfer framing as the frontend. '''
    transfer_id = 'candidate-test-transfer'
    total_chunks = (len(audio) + AUDIO_CHUNK_BYTES - 1) // AUDIO_CHUNK_BYTES
    await communicator.send_json_to({
        'type': 'audio_start',
        'id': transfer_id,
        'mime': 'audio/webm',
        'bytes': len(audio),
        'chunks': total_chunks,
        'manual': manual,
    })

    for offset in range(0, len(audio), AUDIO_CHUNK_BYTES):
        await communicator.send_to(bytes_data=audio[offset:offset + AUDIO_CHUNK_BYTES])

    await communicator.send_json_to({'type': 'audio_end', 'id': transfer_id})

async def receive_opening(communicator):
    ''' Consume the standard opening-question sequence including timing and chunked interviewer audio. '''
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'loading'}
    timing = await communicator.receive_json_from()
    assert timing['type'] == 'timing'
    assert timing['max_minutes'] == INTERVIEW_MAX_MINUTES
    assert timing['wrap_up_minutes'] == INTERVIEW_WRAP_UP_MINUTES
    assert timing['phase'] == 'main'
    assert 0 < timing['remaining_seconds'] <= INTERVIEW_MAX_MINUTES * 60
    assert await communicator.receive_json_from() == {'type': 'history', 'turns': []}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'thinking'}
    assert (await communicator.receive_json_from())['type'] == 'assistant'
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'speaking'}
    audio, _, _ = await receive_audio_transfer(communicator)
    assert audio == b'RIFF-test-audio'
    assert await communicator.receive_json_from() == {'type': 'ready'}

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
    timing = await communicator.receive_json_from()
    assert timing['type'] == 'timing'
    assert timing['max_minutes'] == INTERVIEW_MAX_MINUTES
    history = await communicator.receive_json_from()
    assert history == {'type': 'history', 'turns': []}
    thinking = await communicator.receive_json_from()
    assert thinking == {'type': 'status', 'status': 'thinking'}
    assistant = await communicator.receive_json_from()
    assert assistant['type'] == 'assistant'
    speaking = await communicator.receive_json_from()
    assert speaking == {'type': 'status', 'status': 'speaking'}
    audio, _, _ = await receive_audio_transfer(communicator)
    assert audio == b'RIFF-test-audio'
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
async def test_semantic_end_closes_live_session_without_manual_button(monkeypatch):
    ''' Verify an END stopping decision sends one neutral closing and the existing ended handoff automatically. '''
    user = await sync_to_async(User.objects.create_user)(username='automatic-end@example.com', email='automatic-end@example.com',
        password='A-strong-test-password-42')
    interview = await create_interview(user)
    client = Client()
    await sync_to_async(client.force_login)(user)
    session_cookie = client.cookies['sessionid'].value
    monkeypatch.setattr('interviews.consumers.start_evaluation', no_evaluation)
    monkeypatch.setattr(model_runtime.suite, 'interview_state', lambda *args: 'END')
    headers = [(b'origin', b'http://localhost'), (b'cookie', f'sessionid={session_cookie}'.encode())]
    communicator = WebsocketCommunicator(application, f'/ws/interviews/{interview.id}/', headers=headers)
    connected, _ = await communicator.connect()
    assert connected is True
    await receive_opening(communicator)

    await communicator.send_json_to({'type': 'text', 'text': 'I think that covers everything.'})
    assert await communicator.receive_json_from() == {'type': 'candidate', 'text': 'I think that covers everything.'}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'thinking'}
    closing = await communicator.receive_json_from()
    assert closing['type'] == 'assistant'
    assert 'thank you' in closing['text'].lower()
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'speaking'}
    await receive_audio_transfer(communicator)
    assert await communicator.receive_json_from() == {'type': 'ended'}
    await communicator.disconnect()

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_interviewer_audio_larger_than_websocket_limit_is_chunked(monkeypatch):
    ''' Verify a logical WAV larger than Daphne's default limit is delivered as bounded ordered messages. '''
    user = await sync_to_async(User.objects.create_user)(username='large-audio@example.com', email='large-audio@example.com',
        password='A-strong-test-password-42')
    interview = await create_interview(user)
    client = Client()
    await sync_to_async(client.force_login)(user)
    session_cookie = client.cookies['sessionid'].value
    large_audio = b'RIFF' + (b'a' * ((1024 * 1024) + 12345))
    monkeypatch.setattr(model_runtime.suite, 'speak', lambda text: large_audio)

    headers = [(b'origin', b'http://localhost'), (b'cookie', f'sessionid={session_cookie}'.encode())]
    communicator = WebsocketCommunicator(application, f'/ws/interviews/{interview.id}/', headers=headers)
    connected, _ = await communicator.connect()
    assert connected is True

    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'loading'}
    assert (await communicator.receive_json_from())['type'] == 'timing'
    assert await communicator.receive_json_from() == {'type': 'history', 'turns': []}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'thinking'}
    assert (await communicator.receive_json_from())['type'] == 'assistant'
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'speaking'}
    audio, chunks, start = await receive_audio_transfer(communicator)
    assert audio == large_audio
    assert start['mime'] == 'audio/wav'
    assert start['bytes'] == len(large_audio)
    assert start['chunks'] == len(chunks)
    assert len(chunks) > 1
    assert max(len(chunk) for chunk in chunks) <= AUDIO_CHUNK_BYTES
    assert await communicator.receive_json_from() == {'type': 'ready'}
    await communicator.disconnect()

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_candidate_audio_larger_than_websocket_limit_is_reassembled(monkeypatch):
    ''' Verify large browser recordings arrive in bounded messages and are reconstructed before decoding. '''
    user = await sync_to_async(User.objects.create_user)(username='large-candidate-audio@example.com',
        email='large-candidate-audio@example.com', password='A-strong-test-password-42')
    interview = await create_interview(user)
    client = Client()
    await sync_to_async(client.force_login)(user)
    session_cookie = client.cookies['sessionid'].value
    decoder = Mock(return_value=(np.ones(1600, dtype=np.float32), 16000))
    monkeypatch.setattr('interviews.consumers.decode_browser_audio', decoder)
    large_audio = b'webm' + (b'b' * ((1024 * 1024) + 8192))

    headers = [(b'origin', b'http://localhost'), (b'cookie', f'sessionid={session_cookie}'.encode())]
    communicator = WebsocketCommunicator(application, f'/ws/interviews/{interview.id}/', headers=headers)
    connected, _ = await communicator.connect()
    assert connected is True

    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'loading'}
    assert (await communicator.receive_json_from())['type'] == 'timing'
    assert await communicator.receive_json_from() == {'type': 'history', 'turns': []}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'thinking'}
    assert (await communicator.receive_json_from())['type'] == 'assistant'
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'speaking'}
    await receive_audio_transfer(communicator)
    assert await communicator.receive_json_from() == {'type': 'ready'}

    await send_candidate_audio_transfer(communicator, large_audio, manual=True)
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'transcribing'}
    assert decoder.call_args.args[0] == large_audio
    assert await communicator.receive_json_from() == {
        'type': 'candidate',
        'text': 'I managed commercial cleaning schedules and quality checks.'
    }
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'thinking'}
    assert (await communicator.receive_json_from())['type'] == 'assistant'
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'speaking'}
    await receive_audio_transfer(communicator)
    assert await communicator.receive_json_from() == {'type': 'ready'}
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

    await receive_opening(communicator)

    await send_candidate_audio_transfer(communicator, b'noise')
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

    await receive_opening(communicator)

    await send_candidate_audio_transfer(communicator, b'first-segment')
    assert await communicator.receive_json_from() == {'type': 'turn_pending'}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'listening'}

    await communicator.send_json_to({'type': 'speech_resumed'})
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'listening'}
    await send_candidate_audio_transfer(communicator, b'second-segment')
    assert await communicator.receive_json_from() == {'type': 'turn_pending'}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'listening'}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'transcribing'}

    candidate = await communicator.receive_json_from()
    assert candidate == {'type': 'candidate', 'text': 'I managed commercial cleaning schedules and quality checks.'}
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'thinking'}
    assert (await communicator.receive_json_from())['type'] == 'assistant'
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'speaking'}
    audio, _, _ = await receive_audio_transfer(communicator)
    assert audio == b'RIFF-test-audio'
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

    await receive_opening(communicator)

    await send_candidate_audio_transfer(communicator, b'push-to-talk', manual=True)
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'transcribing'}
    assert await communicator.receive_json_from() == {
        'type': 'candidate',
        'text': 'I managed commercial cleaning schedules and quality checks.'
    }
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'thinking'}
    assert (await communicator.receive_json_from())['type'] == 'assistant'
    assert await communicator.receive_json_from() == {'type': 'status', 'status': 'speaking'}
    audio, _, _ = await receive_audio_transfer(communicator)
    assert audio == b'RIFF-test-audio'
    assert await communicator.receive_json_from() == {'type': 'ready'}
    await communicator.disconnect()

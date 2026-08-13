''' Realtime interview WebSocket handling. '''

import asyncio, base64, json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from ai_interviewer.runtime_config import RUNTIME
from interviews.models import InterviewSession
from interviews.services.audio import decode_browser_audio
from interviews.services.evaluation import start_evaluation
from interviews.services.interview import add_turn, closing_message, finish_interview, opening_message, process_candidate_text, rephrase_message
from interviews.services.runtime import model_runtime

class InterviewConsumer(AsyncWebsocketConsumer):
    ''' Coordinate one live interview over a WebSocket connection. '''

    async def connect(self):
        ''' Accept the socket and initialize connection state. '''
        self.interview_id = self.scope['url_route']['kwargs']['interview_id']
        self.interview = None
        self.authenticated = False
        self.audio_buffer = bytearray()
        self.audio_mime = 'audio/webm'
        self.pending_transcript = ''
        self.connected_client = True
        self.finished = False
        self.timeout_task = None
        self.disconnect_task = None
        self.registered_connection = False
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        ''' Handle candidate audio, text, and interview controls. '''
        if bytes_data is not None:
            await self.receive_audio_chunk(bytes_data)
            return

        if not text_data:
            return

        try:
            message = json.loads(text_data)

        except json.JSONDecodeError:
            await self.send_json({'type': 'error', 'message': 'The interview received an invalid message.'})
            return

        message_type = message.get('type')

        if not self.authenticated:
            if message_type == 'auth':
                await self.authenticate(message.get('token', ''))
            return

        if message_type == 'text':
            await self.handle_candidate_text(message.get('text', ''))
        elif message_type == 'audio_start':
            self.audio_buffer = bytearray()
            self.audio_mime = message.get('mime_type', 'audio/webm')
            await self.send_json({'type': 'status', 'status': 'listening'})
        elif message_type == 'audio_end':
            await self.handle_audio()
        elif message_type == 'confirm_transcript':
            await self.handle_confirmed_transcript(message.get('text', ''))
        elif message_type == 'control':
            await self.handle_control(message.get('action', ''))

    async def receive_audio_chunk(self, audio_chunk):
        ''' Append one audio chunk when the session is authenticated. '''
        if not self.authenticated:
            return

        max_audio_bytes = RUNTIME['interview']['max_audio_bytes']
        if len(self.audio_buffer) + len(audio_chunk) > max_audio_bytes:
            self.audio_buffer = bytearray()
            await self.send_json({'type': 'error', 'message': 'That recording is too large. Please send a shorter answer or type your response.'})
            return

        self.audio_buffer.extend(audio_chunk)

    async def authenticate(self, token):
        ''' Authenticate the WebSocket against the interview session token. '''
        interview = await sync_to_async(self.get_interview)(self.interview_id)
        if not interview or not interview.token_matches(token):
            await self.send_json({'type': 'error', 'message': 'Interview authentication failed.'})
            await self.close(code=4403)
            return

        self.interview = interview
        self.authenticated = True

        inactive_statuses = ['completed', 'terminated', 'evaluating', 'evaluated', 'evaluation_failed']
        if interview.status in inactive_statuses:
            await self.send_json({'type': 'ended', 'message': 'This interview is no longer active.'})
            await self.close(code=1000)
            return

        reserved = await sync_to_async(model_runtime.reserve_interview)(interview.id)
        if not reserved:
            await self.send_json({'type': 'error', 'message': 'The interview worker is currently busy. Please try again shortly.'})
            await self.close(code=4429)
            return

        model_runtime.add_connection(interview.id)
        self.registered_connection = True

        if interview.status == 'created':
            interview.status = 'active'
            interview.started_at = timezone.now()
            await sync_to_async(interview.save)(update_fields=['status', 'started_at'])

        elapsed = (timezone.now() - interview.started_at).total_seconds() if interview.started_at else 0
        remaining = max(0, RUNTIME['interview']['max_minutes'] * 60 - elapsed)
        self.timeout_task = asyncio.create_task(self.end_on_timeout(remaining))
        history = await sync_to_async(self.get_history)(interview)

        if history:
            await self.send_json({'type': 'history', 'turns': history})

        await self.send_json({'type': 'ready', 'language': interview.language})

        if not history:
            await self.send_json({'type': 'status', 'status': 'thinking'})
            reply = await sync_to_async(opening_message)(interview)
            await sync_to_async(add_turn)(interview, 'assistant', reply)
            await self.send_assistant(reply)
            await self.send_json({'type': 'status', 'status': 'ready'})

    def get_interview(self, interview_id):
        ''' Load an interview session by identifier. '''
        return InterviewSession.objects.filter(id=interview_id).first()

    def get_history(self, interview):
        ''' Return ordered conversation history for reconnecting clients. '''
        return list(interview.turns.values('role', 'text'))

    async def handle_candidate_text(self, text):
        ''' Process a typed candidate response. '''
        text = text.strip()[:RUNTIME['interview']['max_text_chars']]
        if not text:
            return

        await self.send_json({'type': 'candidate', 'text': text})
        await self.process_text(text)

    async def handle_audio(self):
        ''' Transcribe a completed candidate recording. '''
        if not self.audio_buffer:
            await self.send_json({'type': 'error', 'message': 'No audio was received.'})
            return

        await self.send_json({'type': 'status', 'status': 'transcribing'})
        audio_bytes = bytes(self.audio_buffer)
        self.audio_buffer = bytearray()
        audio, sample_rate = await sync_to_async(decode_browser_audio)(audio_bytes)

        if audio.size == 0:
            await self.send_json({'type': 'error', 'message': 'The audio could not be decoded. Please try again or type your response.'})
            return

        transcription = await sync_to_async(model_runtime.suite.transcribe)(audio, sample_rate, None)
        text = transcription['text'].strip()
        if not text:
            await self.send_json({'type': 'error', 'message': 'No speech was detected. Please try again or type your response.'})
            return

        await self.send_json({
            'type': 'transcription',
            'text': text,
            'language': transcription.get('language', self.interview.language),
            'requires_confirmation': self.interview.confirm_transcript
        })

        if self.interview.confirm_transcript:
            self.pending_transcript = text
            await self.send_json({'type': 'status', 'status': 'confirming'})
            return

        await self.send_json({'type': 'candidate', 'text': text})
        await self.process_text(text)

    async def handle_confirmed_transcript(self, text):
        ''' Accept a candidate correction to speech recognition output. '''
        if not self.pending_transcript:
            return

        corrected = text.strip() or self.pending_transcript
        self.pending_transcript = ''
        await self.send_json({'type': 'candidate', 'text': corrected})
        await self.process_text(corrected)

    async def process_text(self, text):
        ''' Send one candidate turn through the interview pipeline. '''
        await self.send_json({'type': 'status', 'status': 'thinking'})
        result = await sync_to_async(process_candidate_text)(self.interview, text)
        await self.send_assistant(result['reply'])

        if result['finished']:
            await self.finish_and_evaluate()
        else:
            await self.send_json({'type': 'status', 'status': 'ready'})

    async def handle_control(self, action):
        ''' Handle accessible interview controls from the browser. '''
        if action == 'rephrase':
            await self.send_json({'type': 'status', 'status': 'thinking'})
            reply = await sync_to_async(rephrase_message)(self.interview)
            await sync_to_async(add_turn)(self.interview, 'assistant', reply)
            await self.send_assistant(reply)
            await self.send_json({'type': 'status', 'status': 'ready'})
        elif action == 'end':
            reply = await sync_to_async(closing_message)(self.interview)
            await sync_to_async(add_turn)(self.interview, 'assistant', reply)
            await sync_to_async(finish_interview)(self.interview)
            await self.send_assistant(reply)
            await self.finish_and_evaluate()
        elif action == 'moment':
            await self.send_json({'type': 'status', 'status': 'paused'})

    async def send_assistant(self, text):
        ''' Send interviewer text and synthesized speech to the browser. '''
        await self.send_json({'type': 'assistant', 'text': text})
        await self.send_json({'type': 'status', 'status': 'speaking'})
        audio = await sync_to_async(model_runtime.suite.speak)(text, self.interview.language)

        if audio:
            await self.send_json({
                'type': 'audio',
                'mime_type': 'audio/wav',
                'data': base64.b64encode(audio).decode('ascii')
            })

    async def finish_and_evaluate(self):
        ''' Close the live interview and hand it to the evaluator. '''
        self.finished = True
        await self.send_json({'type': 'ended', 'message': 'The interview is complete.'})
        await sync_to_async(start_evaluation)(self.interview.id)
        await self.close(code=1000)

    async def end_on_timeout(self, seconds):
        ''' End an interview when its configured duration expires. '''
        await asyncio.sleep(seconds)
        current = await sync_to_async(self.get_interview)(self.interview_id)
        if not current or current.status != 'active':
            return

        self.interview = current
        if self.connected_client:
            reply = await sync_to_async(closing_message)(self.interview)
            await sync_to_async(add_turn)(self.interview, 'assistant', reply)
            await sync_to_async(finish_interview)(self.interview)
            await self.send_assistant(reply)
            await self.finish_and_evaluate()
            return

        if model_runtime.has_connection(self.interview_id):
            return

        await sync_to_async(finish_interview)(self.interview)
        await sync_to_async(start_evaluation)(self.interview.id)

    async def end_after_disconnect_grace(self):
        ''' End an abandoned interview after allowing a short reconnect window. '''
        await asyncio.sleep(RUNTIME['interview']['disconnect_grace_seconds'])
        if model_runtime.has_connection(self.interview_id):
            return

        current = await sync_to_async(self.get_interview)(self.interview_id)
        if not current or current.status != 'active':
            return

        await sync_to_async(finish_interview)(current)
        await sync_to_async(start_evaluation)(current.id)

    async def disconnect(self, close_code):
        ''' Release connection state and schedule abandonment handling. '''
        self.connected_client = False
        had_connection = self.registered_connection

        if had_connection:
            model_runtime.remove_connection(self.interview_id)
            self.registered_connection = False

        current_task = asyncio.current_task()
        should_cancel_timeout = self.finished and self.timeout_task and self.timeout_task is not current_task and not self.timeout_task.done()
        if should_cancel_timeout:
            self.timeout_task.cancel()
            return

        if had_connection and not self.finished:
            self.disconnect_task = asyncio.create_task(self.end_after_disconnect_grace())

    async def send_json(self, payload):
        ''' Send one JSON message to the browser. '''
        await self.send(text_data=json.dumps(payload))

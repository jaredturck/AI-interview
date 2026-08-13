''' Realtime interview WebSocket handling. '''

import asyncio, json, logging
from datetime import timedelta

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from interviews.models import InterviewSession
from interviews.services.audio import decode_browser_audio
from interviews.services.evaluation import start_evaluation
from interviews.services.interview import INTERVIEW_MAX_MINUTES, MAX_TEXT_CHARS, add_turn, closing_message, finish_interview, interview_timed_out, \
    opening_message, process_candidate_text, rephrase_message
from interviews.services.runtime import model_runtime

LOGGER = logging.getLogger(__name__)
MAX_AUDIO_BYTES = 20000000
CLOSING_FALLBACK = 'Thank you for your time today. The interview is now complete.'

class InterviewConsumer(AsyncWebsocketConsumer):
    ''' Coordinate one live interview over a WebSocket connection. '''
    async def connect(self):
        ''' Authenticate the candidate and initialize the interview connection. '''
        self.interview_id = self.scope['url_route']['kwargs']['interview_id']
        self.interview = None
        self.pending_transcript = ''
        self.finished = False
        self.evaluation_started = False
        self.timeout_task = None
        user = self.scope['user']

        if not user.is_authenticated:
            await self.close(code=4401)
            return

        self.interview = await sync_to_async(self.get_interview)(self.interview_id, user.id)

        if not self.interview:
            await self.close(code=4404)
            return

        await self.accept()

        if self.interview.status in ['completed', 'terminated', 'evaluating', 'evaluated', 'evaluation_failed']:
            await self.send_json({'type': 'ended', 'status': self.interview.status, 'result': self.interview.result})
            await self.close(code=1000)
            return

        await self.send_json({'type': 'status', 'status': 'loading'})

        try:
            reserved = await sync_to_async(model_runtime.reserve_interview, thread_sensitive=False)(self.interview.id)

        except Exception as error:  # noqa: BLE001
            LOGGER.exception('Live interview models failed to load: %s', error)
            await self.send_json({'type': 'error', 'message': 'The interviewer could not start. Please try again shortly.'})
            await self.close(code=1011)
            return

        if not reserved:
            await self.send_json({'type': 'error', 'message': 'The interview worker is currently busy. Please try again shortly.'})
            await self.close(code=4429)
            return

        if self.interview.status == 'created':
            await sync_to_async(self.activate_interview)()

        if interview_timed_out(self.interview):
            await self.finish_without_closing_message()
            return

        turns = await sync_to_async(self.get_turns)()
        await self.send_json({'type': 'history', 'turns': turns})

        if not turns:
            await self.send_json({'type': 'status', 'status': 'thinking'})

            try:
                opening = await sync_to_async(opening_message, thread_sensitive=False)(self.interview)

            except Exception as error:  # noqa: BLE001
                LOGGER.exception('Opening interviewer generation failed: %s', error)
                await self.send_json({'type': 'error', 'message': 'The interviewer could not start. Please try again shortly.'})
                await self.close(code=1011)
                return

            await sync_to_async(add_turn)(self.interview, 'assistant', opening)
            await self.send_interviewer(opening)
        else:
            await self.send_json({'type': 'ready'})

        self.timeout_task = asyncio.create_task(self.interview_timeout())

    async def disconnect(self, close_code):
        ''' Release connection state without treating a network loss as interview completion. '''
        if self.timeout_task:
            self.timeout_task.cancel()

        if self.interview and not self.evaluation_started:
            model_runtime.release_interview(self.interview.id)

    async def receive(self, text_data=None, bytes_data=None):
        ''' Handle one candidate audio utterance, text message, or interview control. '''
        if self.finished:
            return

        if bytes_data is not None:
            await self.handle_audio(bytes_data)
            return

        if not text_data:
            return

        try:
            message = json.loads(text_data)

        except json.JSONDecodeError:
            await self.send_json({'type': 'error', 'message': 'The interview received an invalid message.'})
            return

        message_type = message.get('type')

        if message_type == 'text':
            self.pending_transcript = ''
            await self.handle_candidate_text(message.get('text', ''))
        elif message_type == 'confirm_transcript':
            await self.handle_confirmed_transcript(message.get('text', ''))
        elif message_type == 'control':
            await self.handle_control(message.get('action', ''))

    async def handle_audio(self, audio_bytes):
        ''' Transcribe one complete browser-recorded utterance. '''
        if self.pending_transcript:
            await self.send_json({'type': 'error', 'message': 'Please confirm or replace the current transcript before recording again.'})
            return

        if len(audio_bytes) > MAX_AUDIO_BYTES:
            await self.send_json({'type': 'error', 'message': 'That recording is too large. Please send a shorter answer or type your response.'})
            return

        await self.send_json({'type': 'status', 'status': 'transcribing'})
        audio, sample_rate = await sync_to_async(decode_browser_audio, thread_sensitive=False)(audio_bytes)

        if audio.size == 0:
            await self.send_json({'type': 'error', 'message': 'I could not read that recording. Please try again or type your response.'})
            return

        try:
            transcript = await sync_to_async(model_runtime.suite.transcribe, thread_sensitive=False)(audio, sample_rate)

        except Exception as error:  # noqa: BLE001
            LOGGER.exception('Speech transcription failed: %s', error)
            await self.send_json({'type': 'error', 'message': 'Speech transcription is temporarily unavailable. You can continue by typing.'})
            await self.send_json({'type': 'ready'})
            return

        if not transcript:
            await self.send_json({'type': 'error', 'message': 'I could not hear enough speech to transcribe that answer.'})
            return

        if self.interview.confirm_transcript:
            self.pending_transcript = transcript
            await self.send_json({'type': 'transcription', 'text': transcript, 'requires_confirmation': True})
            await self.send_json({'type': 'status', 'status': 'confirming'})
            return

        await self.handle_candidate_text(transcript)

    async def handle_confirmed_transcript(self, text):
        ''' Accept the candidate-corrected speech transcript. '''
        if not self.pending_transcript:
            return

        self.pending_transcript = ''
        await self.handle_candidate_text(text)

    async def handle_candidate_text(self, text):
        ''' Process one candidate text turn and return the interviewer response. '''
        text = text.strip()[:MAX_TEXT_CHARS]

        if not text:
            return

        await self.send_json({'type': 'candidate', 'text': text})
        await self.send_json({'type': 'status', 'status': 'thinking'})
        try:
            result = await sync_to_async(process_candidate_text, thread_sensitive=False)(self.interview, text)

        except Exception as error:  # noqa: BLE001
            LOGGER.exception('Interview turn processing failed: %s', error)
            await self.send_json({'type': 'error', 'message': 'The interviewer could not process that turn. Please continue or try again.'})
            await self.send_json({'type': 'ready'})
            return

        if not result['reply']:
            await self.send_json({'type': 'ready'})
            return

        await self.send_interviewer(result['reply'], final=result['finished'])

        if result['finished']:
            await self.complete_live_session()

    async def handle_control(self, action):
        ''' Handle candidate accessibility and interview controls. '''
        if action == 'rephrase':
            await self.send_json({'type': 'status', 'status': 'thinking'})

            try:
                text = await sync_to_async(rephrase_message, thread_sensitive=False)(self.interview)

            except Exception as error:  # noqa: BLE001
                LOGGER.exception('Question rephrasing failed: %s', error)
                await self.send_json({'type': 'error', 'message': 'The interviewer could not rephrase that question right now.'})
                await self.send_json({'type': 'ready'})
                return

            await sync_to_async(add_turn)(self.interview, 'assistant', text)
            await self.send_interviewer(text)
        elif action == 'moment':
            await self.send_json({'type': 'status', 'status': 'paused'})
        elif action == 'end':
            await self.finish_with_closing_message()

    async def send_interviewer(self, text, final=False):
        ''' Send interviewer text followed by WAV audio. '''
        await self.send_json({'type': 'assistant', 'text': text})
        await self.send_json({'type': 'status', 'status': 'speaking'})

        try:
            audio = await sync_to_async(model_runtime.suite.speak, thread_sensitive=False)(text)
            await self.send(bytes_data=audio)

        except Exception as error:  # noqa: BLE001
            LOGGER.exception('Interviewer speech synthesis failed: %s', error)
            await self.send_json({'type': 'audio_unavailable'})

        if not final:
            await self.send_json({'type': 'ready'})

    async def finish_with_closing_message(self):
        ''' Close the interview politely and start final evaluation. '''
        if self.finished:
            return

        self.finished = True
        await self.send_json({'type': 'status', 'status': 'thinking'})

        try:
            text = await sync_to_async(closing_message, thread_sensitive=False)(self.interview)

        except Exception as error:  # noqa: BLE001
            LOGGER.exception('Closing interviewer generation failed: %s', error)
            text = CLOSING_FALLBACK

        await sync_to_async(add_turn)(self.interview, 'assistant', text)
        await sync_to_async(finish_interview)(self.interview)
        await self.send_interviewer(text, final=True)
        await self.complete_live_session()

    async def finish_without_closing_message(self):
        ''' Finish an expired interview that is being resumed after its time limit. '''
        self.finished = True
        await sync_to_async(finish_interview)(self.interview)
        await self.complete_live_session()

    async def complete_live_session(self):
        ''' Notify the candidate and start post-interview evaluation. '''
        if self.timeout_task and self.timeout_task is not asyncio.current_task():
            self.timeout_task.cancel()

        self.timeout_task = None

        self.finished = True
        await self.send_json({'type': 'ended'})
        self.evaluation_started = True
        start_evaluation(self.interview.id)
        await self.close(code=1000)

    async def interview_timeout(self):
        ''' End a connected interview when the 30-minute time limit expires. '''
        if not self.interview.started_at:
            return

        deadline = self.interview.started_at + timedelta(minutes=INTERVIEW_MAX_MINUTES)
        remaining = max(0, (deadline - timezone.now()).total_seconds())

        try:
            await asyncio.sleep(remaining)

        except asyncio.CancelledError:
            return

        if not self.finished:
            await self.finish_with_closing_message()

    async def send_json(self, payload):
        ''' Send one JSON WebSocket message. '''
        await self.send(text_data=json.dumps(payload))

    def activate_interview(self):
        ''' Mark a newly created interview active. '''
        self.interview.status = 'active'
        self.interview.started_at = timezone.now()
        self.interview.save(update_fields=['status', 'started_at'])

    def get_turns(self):
        ''' Return the stored transcript for reconnecting browsers. '''
        return list(self.interview.turns.values('role', 'text'))

    @staticmethod
    def get_interview(interview_id, user_id):
        ''' Return an interview owned by the connected candidate. '''
        return InterviewSession.objects.filter(id=interview_id, user_id=user_id).first()

''' Bridge authenticated browser interview traffic, model services and evaluation through Django Channels. '''

import asyncio, json, logging, uuid
from datetime import timedelta

import numpy as np
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from interviews.models import InterviewSession
from interviews.services.audio import decode_browser_audio
from interviews.services.evaluation import start_evaluation
from interviews.services.interview import INTERVIEW_MAX_MINUTES, INTERVIEW_WRAP_UP_MINUTES, MAX_TEXT_CHARS, add_turn, closing_message, finish_interview, \
    interview_remaining_seconds, interview_timed_out, opening_message, process_candidate_text, rephrase_message
from interviews.services.runtime import model_runtime

LOGGER = logging.getLogger(__name__)
MAX_AUDIO_BYTES = 20000000
AUDIO_CHUNK_BYTES = 256 * 1024
TURN_COMPLETE_GRACE_SECONDS = 0.5
TURN_HOLD_SECONDS = 6
CLOSING_FALLBACK = 'Thank you for your time today. The interview is now complete, and your responses will now be evaluated.'

class InterviewConsumer(AsyncWebsocketConsumer):
    ''' Own the authenticated WebSocket lifecycle for one candidate interview. '''
    async def connect(self):
        ''' Verify ownership, reserve the realtime GPU worker and restore or begin the candidate interview. '''
        self.interview_id = self.scope['url_route']['kwargs']['interview_id']
        self.interview = None
        self.pending_transcript = ''
        self.finished = False
        self.evaluation_started = False
        self.timeout_task = None
        self.turn_finalize_task = None
        self.turn_lock = asyncio.Lock()
        self.interview_action_lock = asyncio.Lock()
        self.audio_send_lock = asyncio.Lock()
        self.pending_turn_audio = []
        self.incoming_audio = None
        self.speech_resumed_since_probe = False
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
            await self.send_json({'type': 'error', 'code': 'interviewer_start_failed',
                'message': 'The interviewer could not start. Please try again shortly.'})
            await self.close(code=4500)
            return

        if not reserved:
            await self.send_json({'type': 'error', 'code': 'worker_busy', 'message': 'The interview worker is currently busy. Please try again shortly.'})
            await self.close(code=4429)
            return

        if self.interview.status == 'created':
            await sync_to_async(self.activate_interview)()

        if interview_timed_out(self.interview):
            await self.finish_without_closing_message()
            return

        await self.send_timing()
        turns = await sync_to_async(self.get_turns)()
        await self.send_json({'type': 'history', 'turns': turns})

        if not turns:
            await self.send_json({'type': 'status', 'status': 'thinking'})

            try:
                opening = await sync_to_async(opening_message, thread_sensitive=False)(self.interview)

            except Exception as error:  # noqa: BLE001
                LOGGER.exception('Opening interviewer generation failed: %s', error)
                await self.send_json({'type': 'error', 'code': 'interviewer_start_failed',
                'message': 'The interviewer could not start. Please try again shortly.'})
                await self.close(code=4500)
                return

            await sync_to_async(add_turn)(self.interview, 'assistant', opening)
            await self.send_interviewer(opening)
        else:
            await self.send_json({'type': 'ready'})

        self.timeout_task = asyncio.create_task(self.interview_timeout())

    async def disconnect(self, close_code):
        ''' Release the GPU-worker reservation after network loss without ending the persisted interview. '''
        if self.timeout_task:
            self.timeout_task.cancel()

        self.cancel_turn_finalize()
        self.incoming_audio = None

        if self.interview and not self.evaluation_started:
            model_runtime.release_interview(self.interview.id)

    async def receive(self, text_data=None, bytes_data=None):
        ''' Route browser audio, typed answers, speech-resume signals, transcript confirmations and controls to their handlers. '''
        if self.finished:
            return

        if bytes_data is not None:
            await self.receive_audio_chunk(bytes_data)
            return

        if not text_data:
            return

        try:
            message = json.loads(text_data)

        except json.JSONDecodeError:
            await self.send_json({'type': 'error', 'code': 'invalid_message', 'message': 'The interview received an invalid message.'})
            return

        message_type = message.get('type')

        if message_type == 'audio_start':
            await self.start_audio_receive(message)
        elif message_type == 'audio_end':
            await self.finish_audio_receive(message)
        elif message_type == 'text':
            self.pending_transcript = ''
            self.reset_pending_turn()
            await self.handle_candidate_text(message.get('text', ''))
        elif message_type == 'speech_resumed':
            await self.handle_speech_resumed()
        elif message_type == 'confirm_transcript':
            await self.handle_confirmed_transcript(message.get('text', ''))
        elif message_type == 'control':
            await self.handle_control(message.get('action', ''))

    async def start_audio_receive(self, message):
        ''' Start one bounded candidate-audio transfer from the browser. '''
        transfer_id = message.get('id')
        total_bytes = message.get('bytes')
        total_chunks = message.get('chunks')

        if not isinstance(transfer_id, str) or not transfer_id or not isinstance(total_bytes, int) or not isinstance(total_chunks, int):
            self.incoming_audio = None
            await self.send_json({'type': 'error', 'code': 'invalid_message', 'message': 'The interview received an invalid message.'})
            return

        if total_bytes < 0 or total_bytes > MAX_AUDIO_BYTES:
            self.incoming_audio = None
            await self.send_json({'type': 'error', 'code': 'recording_too_large',
                'message': 'That recording is too large. Please send a shorter answer or type your response.'})
            return

        expected_chunks = (total_bytes + AUDIO_CHUNK_BYTES - 1) // AUDIO_CHUNK_BYTES

        if total_chunks != expected_chunks:
            self.incoming_audio = None
            await self.send_json({'type': 'error', 'code': 'invalid_message', 'message': 'The interview received an invalid message.'})
            return

        self.incoming_audio = {
            'id': transfer_id,
            'bytes': total_bytes,
            'chunks': total_chunks,
            'received_bytes': 0,
            'parts': [],
            'manual': bool(message.get('manual')),
        }

    async def receive_audio_chunk(self, audio_bytes):
        ''' Append one bounded browser-audio message to the active candidate transfer. '''
        transfer = self.incoming_audio

        if not transfer:
            await self.send_json({'type': 'error', 'code': 'invalid_message', 'message': 'The interview received an invalid message.'})
            return

        if len(audio_bytes) > AUDIO_CHUNK_BYTES or len(transfer['parts']) >= transfer['chunks'] or \
                transfer['received_bytes'] + len(audio_bytes) > transfer['bytes']:
            self.incoming_audio = None
            await self.send_json({'type': 'error', 'code': 'invalid_message', 'message': 'The interview received an invalid message.'})
            return

        transfer['parts'].append(audio_bytes)
        transfer['received_bytes'] += len(audio_bytes)

    async def finish_audio_receive(self, message):
        ''' Validate and reassemble one candidate recording before passing it to the existing speech pipeline. '''
        transfer = self.incoming_audio
        self.incoming_audio = None

        if not transfer or message.get('id') != transfer['id'] or transfer['received_bytes'] != transfer['bytes'] or \
                len(transfer['parts']) != transfer['chunks']:
            await self.send_json({'type': 'error', 'code': 'invalid_message', 'message': 'The interview received an invalid message.'})
            return

        await self.handle_audio(b''.join(transfer['parts']), force_turn=transfer['manual'])

    async def handle_audio(self, audio_bytes, force_turn=False):
        ''' Add one browser speech segment to the pending candidate turn and probe whether the turn is complete. '''
        if self.pending_transcript:
            await self.send_json({'type': 'error', 'code': 'confirm_transcript_first',
                'message': 'Please confirm or replace the current transcript before recording again.'})
            return

        if len(audio_bytes) > MAX_AUDIO_BYTES:
            await self.send_json({'type': 'error', 'code': 'recording_too_large',
                'message': 'That recording is too large. Please send a shorter answer or type your response.'})
            return

        async with self.turn_lock:
            self.cancel_turn_finalize()
            self.speech_resumed_since_probe = False
            audio, sample_rate = await sync_to_async(decode_browser_audio, thread_sensitive=False)(audio_bytes)

            if audio.size == 0:
                await self.send_json({'type': 'error', 'code': 'recording_unreadable',
                    'message': 'I could not read that recording. Please try again or type your response.'})
                return

            try:
                has_speech = await sync_to_async(model_runtime.suite.has_speech, thread_sensitive=False)(audio, sample_rate)

            except Exception as error:  # noqa: BLE001
                LOGGER.exception('Speech activity detection failed: %s', error)
                self.reset_pending_turn()
                await self.send_json({'type': 'error', 'code': 'turn_detection_unavailable',
                    'message': 'Speech detection is temporarily unavailable. You can continue by typing.'})
                await self.send_json({'type': 'ready'})
                return

            if not has_speech:
                pending_turn = bool(self.pending_turn_audio)

                if pending_turn:
                    self.schedule_turn_finalize(TURN_HOLD_SECONDS)

                await self.send_json({'type': 'audio_ignored', 'pending_turn': pending_turn})
                await self.send_json({'type': 'status', 'status': 'listening' if pending_turn else 'ready'})
                return

            self.pending_turn_audio.append(audio)

            if force_turn:
                await self.finalize_pending_turn(sample_rate)
                return

            turn_audio = np.concatenate(self.pending_turn_audio)

            try:
                complete = await sync_to_async(model_runtime.suite.turn_complete, thread_sensitive=False)(turn_audio, sample_rate)

            except Exception as error:  # noqa: BLE001
                LOGGER.exception('Turn completion detection failed: %s', error)
                self.reset_pending_turn()
                await self.send_json({'type': 'error', 'code': 'turn_detection_unavailable',
                    'message': 'Speech turn detection is temporarily unavailable. You can continue by typing.'})
                await self.send_json({'type': 'ready'})
                return

            self.schedule_turn_finalize(TURN_COMPLETE_GRACE_SECONDS if complete else TURN_HOLD_SECONDS)
            await self.send_json({'type': 'turn_pending'})
            await self.send_json({'type': 'status', 'status': 'listening'})

    async def handle_speech_resumed(self):
        ''' Cancel a pending interviewer handoff as soon as the open microphone detects resumed candidate speech. '''
        self.speech_resumed_since_probe = True
        self.cancel_turn_finalize()

        if self.pending_turn_audio:
            await self.send_json({'type': 'status', 'status': 'listening'})

    def schedule_turn_finalize(self, delay):
        ''' Schedule candidate-turn acceptance after either Smart Turn completion grace or the maximum hold period. '''
        self.cancel_turn_finalize()
        self.speech_resumed_since_probe = False
        self.turn_finalize_task = asyncio.create_task(self.finalize_turn_after(delay))

    async def finalize_turn_after(self, delay):
        ''' Finalize the accumulated candidate turn after the selected silence window unless speech resumes first. '''
        try:
            await asyncio.sleep(delay)

        except asyncio.CancelledError:
            return

        self.turn_finalize_task = None

        if self.finished or self.pending_transcript or self.speech_resumed_since_probe:
            return

        async with self.turn_lock:
            if not self.finished and self.pending_turn_audio and not self.speech_resumed_since_probe:
                await self.finalize_pending_turn(16000)

    async def finalize_pending_turn(self, sample_rate):
        ''' Transcribe one accepted accumulated turn and pass confirmed text into the existing interview policy pipeline. '''
        if not self.pending_turn_audio:
            return

        turn_audio = np.concatenate(self.pending_turn_audio)
        await self.send_json({'type': 'status', 'status': 'transcribing'})

        try:
            transcript = await sync_to_async(model_runtime.suite.transcribe, thread_sensitive=False)(turn_audio, sample_rate)

        except Exception as error:  # noqa: BLE001
            LOGGER.exception('Speech transcription failed: %s', error)
            self.reset_pending_turn()
            await self.send_json({'type': 'error', 'code': 'transcription_unavailable',
                'message': 'Speech transcription is temporarily unavailable. You can continue by typing.'})
            await self.send_json({'type': 'ready'})
            return

        if self.speech_resumed_since_probe:
            await self.send_json({'type': 'turn_pending'})
            await self.send_json({'type': 'status', 'status': 'listening'})
            return

        self.pending_turn_audio = []

        if not transcript:
            await self.send_json({'type': 'error', 'code': 'transcription_empty', 'message': 'I could not hear enough speech to transcribe that answer.'})
            await self.send_json({'type': 'ready'})
            return

        if self.interview.confirm_transcript:
            self.pending_transcript = transcript
            await self.send_json({'type': 'transcription', 'text': transcript, 'requires_confirmation': True})
            await self.send_json({'type': 'status', 'status': 'confirming'})
            return

        await self.handle_candidate_text(transcript)

    def cancel_turn_finalize(self):
        ''' Cancel a scheduled candidate-turn handoff without interrupting model work that has already begun. '''
        task = self.turn_finalize_task
        self.turn_finalize_task = None

        if task and task is not asyncio.current_task():
            task.cancel()

    def reset_pending_turn(self):
        ''' Discard uncommitted microphone audio when another explicit candidate input path takes ownership. '''
        self.cancel_turn_finalize()
        self.pending_turn_audio = []
        self.speech_resumed_since_probe = False

    async def handle_confirmed_transcript(self, text):
        ''' Replace ASR output with the candidate-approved transcript before interview processing continues. '''
        if not self.pending_transcript:
            return

        self.pending_transcript = ''
        await self.handle_candidate_text(text)

    async def handle_candidate_text(self, text):
        ''' Send one candidate answer through interview policy and model processing, then return the resulting interviewer turn. '''
        text = text.strip()[:MAX_TEXT_CHARS]

        if not text:
            return

        async with self.interview_action_lock:
            if self.finished:
                return

            await self.send_json({'type': 'candidate', 'text': text})
            await self.send_json({'type': 'status', 'status': 'thinking'})
            try:
                result = await sync_to_async(process_candidate_text, thread_sensitive=False)(self.interview, text)

            except Exception as error:  # noqa: BLE001
                LOGGER.exception('Interview turn processing failed: %s', error)
                await self.send_json({'type': 'error', 'code': 'turn_failed',
                    'message': 'The interviewer could not process that turn. Please continue or try again.'})
                await self.send_json({'type': 'ready'})
                return

            if not result['reply']:
                await self.send_json({'type': 'ready'})
                return

            await self.send_interviewer(result['reply'], final=result['finished'])

            if result['finished']:
                await self.complete_live_session()

    async def handle_control(self, action):
        ''' Support rephrase, pause and candidate-ended controls without treating them as answer turns. '''
        if action == 'rephrase':
            async with self.interview_action_lock:
                if self.finished:
                    return

                await self.send_json({'type': 'status', 'status': 'thinking'})

                try:
                    text = await sync_to_async(rephrase_message, thread_sensitive=False)(self.interview)

                except Exception as error:  # noqa: BLE001
                    LOGGER.exception('Question rephrasing failed: %s', error)
                    await self.send_json({'type': 'error', 'code': 'rephrase_failed',
                        'message': 'The interviewer could not rephrase that question right now.'})
                    await self.send_json({'type': 'ready'})
                    return

                await sync_to_async(add_turn)(self.interview, 'assistant', text)
                await self.send_interviewer(text)
        elif action == 'moment':
            await self.send_json({'type': 'status', 'status': 'paused'})
        elif action == 'end':
            async with self.interview_action_lock:
                await self.finish_with_closing_message()

    async def send_interviewer(self, text, final=False):
        ''' Deliver interviewer text immediately and pair it with best-effort Qwen3-TTS audio. '''
        await self.send_json({'type': 'assistant', 'text': text})
        await self.send_json({'type': 'status', 'status': 'speaking'})

        try:
            audio = await sync_to_async(model_runtime.suite.speak, thread_sensitive=False)(text)
            await self.send_audio(audio)

        except Exception as error:  # noqa: BLE001
            LOGGER.exception('Interviewer speech synthesis failed: %s', error)
            await self.send_json({'type': 'audio_unavailable'})

        if not final:
            await self.send_json({'type': 'ready'})

    async def send_audio(self, audio):
        ''' Send one logical WAV as bounded WebSocket messages so transport limits never depend on utterance length. '''
        transfer_id = uuid.uuid4().hex
        total_bytes = len(audio)
        total_chunks = (total_bytes + AUDIO_CHUNK_BYTES - 1) // AUDIO_CHUNK_BYTES

        async with self.audio_send_lock:
            await self.send_json({
                'type': 'audio_start',
                'id': transfer_id,
                'mime': 'audio/wav',
                'bytes': total_bytes,
                'chunks': total_chunks,
            })

            for offset in range(0, total_bytes, AUDIO_CHUNK_BYTES):
                await self.send(bytes_data=audio[offset:offset + AUDIO_CHUNK_BYTES])

            await self.send_json({'type': 'audio_end', 'id': transfer_id})

    async def finish_with_closing_message(self):
        ''' Persist a final interviewer closing, end the live session and hand the interview to post-interview evaluation. '''
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
        ''' End a resumed interview that already exceeded 15 minutes without generating an extra closing turn. '''
        self.finished = True
        await sync_to_async(finish_interview)(self.interview)
        await self.complete_live_session()

    async def complete_live_session(self):
        ''' Close the live WebSocket cleanly and hand the completed interview to background evaluation. '''
        self.reset_pending_turn()

        if self.timeout_task and self.timeout_task is not asyncio.current_task():
            self.timeout_task.cancel()

        self.timeout_task = None

        self.finished = True
        await self.send_json({'type': 'ended'})
        self.evaluation_started = True
        start_evaluation(self.interview.id)
        await self.close(code=1000)

    async def interview_timeout(self):
        ''' Enforce the 15-minute hard limit while a candidate remains connected. '''
        if not self.interview.started_at:
            return

        deadline = self.interview.started_at + timedelta(minutes=INTERVIEW_MAX_MINUTES)
        remaining = max(0, (deadline - timezone.now()).total_seconds())

        try:
            await asyncio.sleep(remaining)

        except asyncio.CancelledError:
            return

        async with self.interview_action_lock:
            if not self.finished:
                await self.finish_with_closing_message()

    async def send_timing(self):
        ''' Send server-authoritative interview timing so the browser countdown does not depend on client clock agreement. '''
        await self.send_json({
            'type': 'timing',
            'remaining_seconds': interview_remaining_seconds(self.interview),
            'max_minutes': INTERVIEW_MAX_MINUTES,
            'wrap_up_minutes': INTERVIEW_WRAP_UP_MINUTES,
            'phase': self.interview.phase,
        })

    async def send_json(self, payload):
        ''' Keep WebSocket control and status messages serialized through one JSON helper. '''
        await self.send(text_data=json.dumps(payload))

    def activate_interview(self):
        ''' Start the persisted interview clock when its first WebSocket session reserves the worker. '''
        self.interview.status = 'active'
        self.interview.started_at = timezone.now()
        self.interview.save(update_fields=['status', 'started_at'])
        self.interview.application.status = 'interview_in_progress'
        self.interview.application.save(update_fields=['status'])

    def get_turns(self):
        ''' Restore persisted role and text history when a candidate reconnects to an active interview. '''
        return list(self.interview.turns.values('role', 'text'))

    @staticmethod
    def get_interview(interview_id, user_id):
        ''' Enforce candidate ownership when resolving a WebSocket interview ID. '''
        return InterviewSession.objects.select_related('application__job').filter(id=interview_id, application__user_id=user_id).first()

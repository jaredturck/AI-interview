''' Replace GPU-backed model services with deterministic fixtures across interview tests. '''

import pytest

from interviews.services.runtime import model_runtime

class FakeModelSuite:
    ''' Mirror the production model-suite interface without loading Qwen checkpoints during tests. '''
    def load_live(self):
        ''' Satisfy realtime preload calls without allocating GPU models during tests. '''
        return None

    def live_loaded(self):
        ''' Keep runtime capacity checks available while tests use the fake model suite. '''
        return True

    def load_evaluator(self):
        ''' Satisfy evaluator handoff without loading Qwen3.6 during tests. '''
        return None

    def unload_evaluator(self):
        ''' Mirror evaluator cleanup without holding GPU model state during tests. '''
        return None

    def transcribe(self, audio, sample_rate):
        ''' Provide predictable ASR text for tests that exercise spoken interview turns. '''
        return 'I built a Python API with PostgreSQL.'

    def speak(self, text):
        ''' Provide minimal WAV-like bytes so WebSocket audio delivery can be tested without Qwen3-TTS. '''
        return b'RIFF-test-audio'

    def guard_user(self, text):
        ''' Drive unsafe-request routing with one deterministic guard phrase while leaving other test input safe. '''
        return 'Unsafe' if 'steal credentials' in text.lower() else 'Safe'

    def guard_response(self, user_text, assistant_text):
        ''' Keep fake interviewer output on the normal safe-response path during tests. '''
        return 'Safe'

    def interviewer(self, system_prompt, turns, max_tokens=32):
        ''' Drive opening, follow-up, redirect, rephrase and closing paths with deterministic interviewer text. '''
        if 'End the interview now' in system_prompt:
            return 'Thank you for your time today.'

        if 'Rephrase the last interviewer question' in system_prompt:
            return 'What part of that project did you build?'

        if 'unsafe' in system_prompt.lower():
            return 'I can\'t help with that. What technical project would you like to discuss?'

        if 'steer the conversation back' in system_prompt:
            return 'Let\'s return to the interview. What technical experience would you like to discuss?'

        if turns:
            return 'What was your role in building that project?'

        return 'Tell me about a software project you have worked on.'

    def misuse(self, transcript):
        ''' Drive redirect and termination paths from repeated cake requests in the test transcript. '''
        count = transcript.lower().count('bake a cake')

        if count >= 3:
            return 'TERMINATE'

        if count:
            return 'REDIRECT'

        return 'CONTINUE'

    def evaluate_question(self, job_description, transcript, question):
        ''' Provide stable criterion evidence so evaluation persistence can be tested without Qwen3.6. '''
        return f'The transcript provides relevant evidence for: {question}'

    def final_choice(self, job_description, transcript, answers):
        ''' Provide a fixed PROGRESS outcome so final evaluation persistence remains deterministic in tests. '''
        return 'PROGRESS'

@pytest.fixture(autouse=True)
def fake_model_runtime():
    ''' Install FakeModelSuite process-wide for each test and reset runtime ownership around it. '''
    original_suite = model_runtime._suite
    model_runtime._suite = FakeModelSuite()
    model_runtime.active_interview_id = None
    model_runtime.evaluating = False
    yield
    model_runtime._suite = original_suite
    model_runtime.active_interview_id = None
    model_runtime.evaluating = False

''' Shared interview test fixtures. '''

import pytest

from interviews.services.runtime import model_runtime

class FakeModelSuite:
    ''' Provide deterministic lightweight model behaviour for application tests. '''
    def load_live(self):
        ''' Simulate loading the live model stack. '''
        return None

    def load_evaluator(self):
        ''' Simulate loading the evaluator. '''
        return None

    def unload_evaluator(self):
        ''' Simulate unloading the evaluator. '''
        return None

    def transcribe(self, audio, sample_rate):
        ''' Return a stable test transcription. '''
        return 'I built a Python API with PostgreSQL.'

    def speak(self, text):
        ''' Return small fake WAV bytes. '''
        return b'RIFF-test-audio'

    def guard_user(self, text):
        ''' Mark the test unsafe phrase as unsafe. '''
        return 'Unsafe' if 'steal credentials' in text.lower() else 'Safe'

    def guard_response(self, user_text, assistant_text):
        ''' Treat generated test interviewer output as safe. '''
        return 'Safe'

    def interviewer(self, system_prompt, turns, max_tokens=32):
        ''' Generate deterministic interviewer text from the current test context. '''
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
        ''' Escalate repeated cake requests in the test transcript. '''
        count = transcript.lower().count('bake a cake')

        if count >= 3:
            return 'TERMINATE'

        if count:
            return 'REDIRECT'

        return 'CONTINUE'

    def evaluate_question(self, job_description, transcript, question):
        ''' Return a stable criterion assessment. '''
        return f'The transcript provides relevant evidence for: {question}'

    def final_choice(self, job_description, transcript, answers):
        ''' Return a stable final test outcome. '''
        return 'PROGRESS'

@pytest.fixture(autouse=True)
def fake_model_runtime():
    ''' Replace heavy Qwen inference with a deterministic test suite. '''
    original_suite = model_runtime._suite
    model_runtime._suite = FakeModelSuite()
    model_runtime.active_interview_id = None
    model_runtime.evaluating = False
    yield
    model_runtime._suite = original_suite
    model_runtime.active_interview_id = None
    model_runtime.evaluating = False

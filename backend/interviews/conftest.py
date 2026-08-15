''' Replace GPU-backed model services with deterministic fixtures across interview tests. '''

import pytest

from interviews.services.runtime import model_runtime

class FakeModelSuite:
    ''' Mirror the production model-suite interface without loading Qwen checkpoints during tests. '''
    def load_models(self):
        ''' Satisfy resident model preload calls without allocating GPU models during tests. '''
        return None

    def models_loaded(self):
        ''' Keep runtime capacity checks available while tests use the fake model suite. '''
        return True

    def has_speech(self, audio, sample_rate):
        ''' Treat non-empty test audio as speech unless a test overrides the fake detector. '''
        return bool(audio.size)

    def turn_complete(self, audio, sample_rate):
        ''' Treat test speech as a completed turn unless a test overrides the fake detector. '''
        return True

    def transcribe(self, audio, sample_rate):
        ''' Provide predictable ASR text for tests that exercise spoken interview turns. '''
        return 'I managed commercial cleaning schedules and quality checks.'

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
        if turns and turns[-1]['text'].startswith('End the interview now'):
            return 'Thank you for your time today.'

        if turns and turns[-1]['text'].startswith('Rephrase the last interviewer question'):
            return 'Could you describe your part in that work another way?'

        if 'unsafe' in system_prompt.lower():
            return 'I can\'t help with that request. Could you tell me more about your relevant experience?'

        if 'steer the conversation back' in system_prompt:
            return 'Let\'s return to the interview. Could you tell me more about your relevant experience?'

        if turns and turns[-1]['text'].startswith('Begin the interview with one relevant opening question'):
            return 'Could you tell me about experience that is relevant to this role?'

        return 'What responsibilities did you personally handle in that work?'

    def misuse(self, transcript):
        ''' Drive redirect and termination paths from repeated cake requests in the test transcript. '''
        count = transcript.lower().count('bake a cake')

        if count >= 3:
            return 'TERMINATE'

        if count:
            return 'REDIRECT'

        return 'CONTINUE'

    def evaluate_criteria(self, job_description, transcript, criteria):
        ''' Return one deterministic positive structured assessment for every configured test criterion. '''
        assessments = []

        for criterion in criteria:
            criterion_type = criterion['criterion_type']
            question = criterion['question']

            if criterion_type == 'verification':
                assessment = 'CLAIMED'
            elif criterion_type == 'essential':
                assessment = 'MET'
            else:
                assessment = 'POSITIVE'
            assessments.append({
                'question_index': criterion['question_index'],
                'criterion_type': criterion_type,
                'question': question,
                'assessment': assessment,
                'answer': f'The transcript provides relevant evidence for: {question}',
            })

        return {'assessments': assessments, 'error': ''}

    def final_evaluation(self, job_description, transcript, assessments):
        ''' Return a stable holistic progression result after application hard gates pass. '''
        return {'result': 'PROGRESS', 'error': ''}

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

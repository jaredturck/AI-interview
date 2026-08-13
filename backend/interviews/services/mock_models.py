''' Lightweight deterministic model substitutes for development and tests. '''
import io, re, wave

import numpy as np

class MockModelSuite:
    ''' Mimic the real model suite without loading model weights. '''
    def __init__(self):
        ''' Start the mock suite in live interview mode. '''
        self.mode = 'live'

    def unload_live(self):
        ''' Mark live mock models as unloaded. '''
        self.mode = 'idle'

    def unload_evaluator(self):
        ''' Mark the mock evaluator as unloaded. '''
        self.mode = 'idle'

    def load_live(self):
        ''' Mark live mock models as available. '''
        self.mode = 'live'

    def load_evaluator(self):
        ''' Mark the mock evaluator as available. '''
        self.mode = 'evaluator'

    def transcribe(self, audio, sample_rate, language=None):
        ''' Return a stable fake speech transcription. '''
        return {'text': 'Mock audio transcription.', 'language': language or 'English'}

    def speak(self, text, language):
        ''' Return a short silent WAV as mock synthesized speech. '''
        sample_rate = 16000
        duration = 0.12
        samples = int(sample_rate * duration)
        waveform = np.zeros(samples, dtype=np.int16)
        output = io.BytesIO()

        with wave.open(output, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(waveform.tobytes())

        return output.getvalue()

    def guard_user(self, text):
        ''' Classify a small deterministic set of unsafe test inputs. '''
        lowered = text.lower()
        unsafe_terms = ['steal passwords', 'steal credentials', 'malware payload', 'buy stolen accounts', 'expose private data']
        return 'Unsafe' if any(term in lowered for term in unsafe_terms) else 'Safe'

    def guard_response(self, user_text, assistant_text):
        ''' Treat mock interviewer output as safe. '''
        return 'Safe'

    def interviewer(self, system_prompt, turns, max_tokens=40):
        ''' Produce a deterministic short follow-up from the mock transcript. '''
        candidate_turns = [turn['text'] for turn in turns if turn['role'] == 'user']

        if 'End the interview now' in system_prompt:
            return 'Thank you for your time today. It was good speaking with you.'

        if 'latest request is unsafe' in system_prompt:
            return 'I can\'t help with that request. Let\'s return to your technical experience. What have you been working on recently?'

        if 'Briefly steer the conversation back' in system_prompt:
            return 'Let\'s return to your technical experience. What software work have you done recently?'

        if 'Rephrase the last interviewer question' in system_prompt:
            return 'Could you explain that part of your experience more simply, starting with what you personally worked on?'

        if not candidate_turns:
            return 'Could you tell me about a software project you\'ve worked on recently?'

        last = candidate_turns[-1]
        technologies = re.findall(r'\b(Python|Django|PHP|Java|JavaScript|PostgreSQL|SQL|React|AWS|Redis|Celery)\b', last, re.I)

        if technologies:
            return f'What did you personally use {technologies[0]} for in that project?'

        if len(last.split()) < 8:
            return 'What part of that work did you personally build or change?'

        return 'What was the most technically difficult part of that work, and how did you approach it?'

    def misuse(self, transcript):
        ''' Return deterministic misuse states for development tests. '''
        lowered = transcript.lower()
        markers = ['bake a cake', 'pretend you\'re', 'system prompt', 'turn on your mic']
        score = sum(lowered.count(marker) for marker in markers)

        if score >= 3:
            return 'TERMINATE'

        if score >= 1:
            return 'REDIRECT'

        return 'CONTINUE'

    def should_end(self, transcript):
        ''' End long mock interviews after enough candidate turns. '''
        candidate_turns = transcript.count('Candidate:')
        return 'END' if candidate_turns >= 10 else 'CONTINUE'

    def evaluate_question(self, job_description, transcript, question):
        ''' Return a deterministic mock assessment for one criterion. '''
        return (f'The transcript contains evidence relevant to this criterion. Review focus: {question} '
            'Candidate evidence should be weighed against the role as a whole.')

    def synthesize(self, job_description, transcript, answers):
        ''' Produce a deterministic mock synthesis from simple technical terms. '''
        technical_terms = ['python', 'django', 'database', 'sql', 'api', 'debug', 'backend']
        score = sum(1 for term in technical_terms if term in transcript.lower())
        recommendation = 'PROGRESS' if score >= 3 else 'NOT_PROGRESS'
        return f'The candidate\'s evidence has been considered across all criteria. Recommended outcome: {recommendation}.'

    def final_choice(self, job_description, transcript, answers, synthesis):
        ''' Return the binary mock decision encoded in the synthesis. '''
        return 'PROGRESS' if 'Recommended outcome: PROGRESS' in synthesis else 'NOT_PROGRESS'

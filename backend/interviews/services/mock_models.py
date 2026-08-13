import io
import math
import re
import wave

import numpy as np


class MockModelSuite:
    def __init__(self):
        self.mode = "live"

    def unload_live(self):
        self.mode = "idle"

    def unload_evaluator(self):
        self.mode = "idle"

    def load_live(self):
        self.mode = "live"

    def load_evaluator(self):
        self.mode = "evaluator"

    def transcribe(self, audio, sample_rate, language=None):
        return {"text": "Mock audio transcription.", "language": language or "English"}

    def speak(self, text, language):
        sample_rate = 16000
        duration = 0.12
        samples = int(sample_rate * duration)
        waveform = np.zeros(samples, dtype=np.int16)
        output = io.BytesIO()
        with wave.open(output, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(waveform.tobytes())
        return output.getvalue()

    def guard_user(self, text):
        lowered = text.lower()
        unsafe_terms = ["steal passwords", "steal credentials", "malware payload", "buy stolen accounts", "expose private data"]
        return "Unsafe" if any(term in lowered for term in unsafe_terms) else "Safe"

    def guard_response(self, user_text, assistant_text):
        return "Safe"

    def interviewer(self, system_prompt, turns, max_tokens=40):
        candidate_turns = [turn["text"] for turn in turns if turn["role"] == "user"]
        if "End the interview now" in system_prompt:
            return "Thank you for your time today. It was good speaking with you."
        if "latest request is unsafe" in system_prompt:
            return "I can't help with that request. Let's return to your technical experience—what have you been working on recently?"
        if "Briefly steer the conversation back" in system_prompt:
            return "Let's return to your technical experience. What software work have you done recently?"
        if "Rephrase the last interviewer question" in system_prompt:
            return "Could you explain that part of your experience in a simpler way, starting with what you personally worked on?"
        if not candidate_turns:
            return "Could you tell me about a software project you've worked on recently?"
        last = candidate_turns[-1]
        technologies = re.findall(r"\b(Python|Django|PHP|Java|JavaScript|PostgreSQL|SQL|React|AWS|Redis|Celery)\b", last, re.I)
        if technologies:
            return f"What did you personally use {technologies[0]} for in that project?"
        if len(last.split()) < 8:
            return "What part of that work did you personally build or change?"
        return "What was the most technically difficult part of that work, and how did you approach it?"

    def misuse(self, transcript):
        lowered = transcript.lower()
        markers = ["bake a cake", "pretend you're", "system prompt", "turn on your mic"]
        score = sum(lowered.count(marker) for marker in markers)
        if score >= 3:
            return "TERMINATE"
        if score >= 1:
            return "REDIRECT"
        return "CONTINUE"

    def should_end(self, transcript):
        candidate_turns = transcript.count("Candidate:")
        return "END" if candidate_turns >= 10 else "CONTINUE"

    def evaluate_question(self, job_description, transcript, question):
        return f"The transcript contains evidence relevant to this criterion. Review focus: {question} Candidate evidence should be weighed against the role as a whole."

    def synthesize(self, job_description, transcript, answers):
        technical_terms = ["python", "django", "database", "sql", "api", "debug", "backend"]
        score = sum(1 for term in technical_terms if term in transcript.lower())
        recommendation = "PROGRESS" if score >= 3 else "NOT_PROGRESS"
        return f"The candidate's evidence has been considered across all criteria. Recommended outcome: {recommendation}."

    def final_choice(self, job_description, transcript, answers, synthesis):
        return "PROGRESS" if "Recommended outcome: PROGRESS" in synthesis else "NOT_PROGRESS"

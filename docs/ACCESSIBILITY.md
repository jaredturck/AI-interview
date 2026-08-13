# Accessibility checklist

The design target is WCAG 2.2 AA plus an interview-specific principle: measure relevant technical evidence rather than a candidate's ability to cope with one communication format.

## Input and output

- Voice input is optional; typed responses use the same interview path.
- Interviewer speech is duplicated as visible text.
- Interviewer voice can be muted while text remains fully usable.
- The current question remains visible in the transcript.
- Optional transcription confirmation lets a candidate correct ASR errors before model processing.
- Replay and rephrase controls do not require the candidate to verbally request an adjustment.
- Speech playback speed is adjustable client-side.
- Microphone failure never blocks typed participation.

## Timing and speech

V1 deliberately uses explicit press-to-record / **Finish speaking** controls rather than ending a turn after a short silence. A candidate can pause for as long as they need inside the speaking turn, subject only to the overall interview time limit.

The **I need a moment** control pauses interviewer audio and visibly marks the conversation as paused.

## Interaction

- Native `button`, `input`, `select` and `textarea` elements are used.
- Every actionable control has visible keyboard focus.
- Primary control heights are at least approximately 44 CSS pixels.
- Interviewer responses are announced through a polite ARIA live region after complete text arrives.
- Dynamic interview/evaluation status is exposed through status/live regions.
- Focus is not automatically stolen when new transcript messages appear.
- The interface does not use colour as the only status signal.
- Reduced-motion preferences disable non-essential animation/transitions.
- Browser text scaling/zoom is supported by responsive layouts rather than fixed-size panels.

## Interview behaviour

The interviewer is instructed to:

- ask one clear question at a time;
- use the job description as direction rather than a rigid questionnaire;
- follow productive technical threads while they continue yielding useful information;
- make questions simpler, narrower or more concrete when the current style is not producing useful answers;
- allow detailed candidates to explore relevant work deeply;
- keep its own turns short so the candidate has conversational space.

This adaptation is based on the success of the current conversation, not on diagnosing or labelling the candidate.

## Candidate agency

Before starting, the interface explains the automated interview/initial decision, voice/text options, transcript handling and an external recruitment contact for adjustments not covered by the interface.

After the interview, the candidate can request human review and explain what they believe went wrong. That mechanism is separate from the AI decision itself.

## Before production

Test with:

- keyboard-only navigation;
- NVDA/JAWS/VoiceOver or other representative screen readers;
- browser zoom/text scaling at 200%;
- voice muted with text-only interviewer output;
- text-only candidate participation;
- speech differences and varied accents;
- noisy/low-quality microphones;
- deliberately long pauses during spoken answers;
- candidates who prefer broad questions and candidates who need concrete questions;
- real disabled and neurodivergent participants.

Automated accessibility scanners are useful but cannot replace those tests.

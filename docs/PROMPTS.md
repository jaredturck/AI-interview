# Prompts

Prompts are deliberately stored as short editable text files under `prompts/`.

## Realtime interviewer

`interviewer.txt` defines the live model as a brief, adaptive evidence-gathering technical interviewer. The job description is appended at runtime from `config/job_description.md`.

The prompt intentionally avoids example interview questions so a small model is not unnecessarily anchored to particular technologies or wording.

## Misuse monitor

`misuse.txt` asks the separate misuse model to choose `CONTINUE`, `REDIRECT` or `TERMINATE`. The monitor is intentionally forgiving of isolated unusual behaviour and only terminates sustained clear misuse.

## Evaluator

`evaluator_question.txt` is used independently for every line in `config/evaluation_questions.txt`.

`evaluator_synthesis.txt` combines those focused assessments.

`final_choice.txt` drives a final thinking pass over the complete evidence. `final_output.txt` is used only for the constrained application-facing `PROGRESS` or `NOT_PROGRESS` decision.

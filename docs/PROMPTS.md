# Prompts

Prompts are deliberately short and stored under `prompts/`.

## `interviewer.txt`

Defines the realtime model as a friendly, adaptive technical interviewer whose job is to gather useful evidence. The job description is appended by the application. It intentionally contains no example interview questions so the small realtime model is not anchored to specific technologies or wording.

## `misuse.txt`

Asks the separate misuse model to choose `CONTINUE`, `REDIRECT` or `TERMINATE`. It is intentionally forgiving of isolated unusual behavior and only terminates sustained clear misuse.

## `evaluator_question.txt`

Used independently for every line in `config/evaluation_questions.txt`. Each call focuses the evaluator's reasoning on one criterion while retaining the complete job description and transcript.

## `final_choice.txt`

Runs one final reasoning pass over the original evidence and all completed criterion assessments.

## `final_output.txt`

Used only for the mechanically constrained application-facing `PROGRESS` or `NOT_PROGRESS` output.

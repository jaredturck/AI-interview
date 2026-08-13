# Prompts

Prompts are deliberately short, role-neutral and stored under `prompts/`. Occupation-specific content belongs in the Job description and evaluation rubric, not generic application prompts.

## `interviewer.txt`

Defines a friendly adaptive first-stage interviewer. It gathers job-relevant evidence from the linked Job description without assuming a technical occupation or embedding example questions.

## `misuse.txt`

Asks the separate misuse model to choose `CONTINUE`, `REDIRECT` or `TERMINATE`. It is forgiving of isolated confusion/tangents and terminates only sustained clear misuse.

## `evaluator_question.txt`

Used once for every criterion stored with the Job. Each call assesses job-relevant evidence while retaining the complete Job description and transcript.

## `final_choice.txt`

Runs final reasoning over the original evidence and all completed criterion assessments without assuming a particular occupation.

## `final_output.txt`

Used only for mechanically constrained `PROGRESS` or `NOT_PROGRESS` output.

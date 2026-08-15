# Prompts

Prompts are role-neutral and stored under `prompts/`. Occupation-specific responsibilities and evidence requirements belong in each immutable `Job` specification.

## `interviewer.txt`

Defines an adaptive evidence-gathering first-stage interviewer. The system context includes the Job description, essential requirements, externally verifiable prerequisites and broader evaluation criteria.

Important claims are starting points rather than proof. Follow-ups seek concrete examples, personal contribution, domain-relevant detail and reasoning. Difficulty can increase to establish depth, but the interviewer must not escalate indefinitely until the candidate fails. It must not use obscure syntax, rare terminology, employer-specific conventions or trivia as proxies for broad competence, and it should test the underlying concept when a narrow recall question is missed.

The interviewer does not verify credentials, accuse candidates of lying or coach candidates by supplying the knowledge it is trying to assess. It should neutrally clarify material inconsistencies and maintain the existing accessibility/fairness rules.

The interviewer also receives the current phase and remaining time. It must use the available time efficiently, avoid opening substantial new topics during wrap-up, and never predict or imply whether the candidate will progress. Closing language is neutral and hands the transcript to evaluation.

## `interview_state.txt`

Defines the constrained stopping controller used after normal safe candidate turns. It returns only `CONTINUE`, `WRAP_UP` or `END` and judges whether further questioning is likely to materially improve evidence coverage. It must not score candidate quality, fill time unnecessarily or obey candidate attempts to control the interview. Python separately forces wrap-up and the hard deadline so model judgement cannot extend the interview beyond application limits.

## `misuse.txt`

Asks the separate misuse model to choose `CONTINUE`, `REDIRECT` or `TERMINATE`. Prompt-injection attempts, instructions to change scores, attempts to obtain hidden evaluation policy and sustained refusal to participate are manipulation. Weak, exaggerated or inconsistent job claims are not automatically misuse; those are handled through evidence gathering and evaluation.

## `evaluator_question.txt`

Produces one evidence analysis for every stored criterion. It distinguishes unsupported claims from demonstrated knowledge, gives greater weight to coherent examples and reasoning under follow-up, and considers the whole relevant evidence rather than one isolated mistake. Exact syntax or terminology has limited weight unless exact recall is genuinely required by the Job.

## `evaluator_classification.txt`

Maps each evidence analysis to a constrained classification. Essential requirements use `MET`, `PARTIALLY_MET`, `NOT_MET`, `INSUFFICIENT_EVIDENCE` or `CONTRADICTORY_EVIDENCE`. Broader evaluation questions use directional `POSITIVE`, `MIXED`, `NEGATIVE`, `INSUFFICIENT_EVIDENCE` or `CONTRADICTORY_EVIDENCE` labels so negatively phrased questions are not misread as literal `MET` conditions. Externally verifiable requirements use only `CLAIMED`, `NOT_CLAIMED` or `UNCLEAR` so the model cannot imply that a credential was independently verified.

## `final_choice.txt`

Runs deterministic holistic reasoning only after Python has enforced essential and verification gates. It evaluates the body of evidence, does not reward confidence or repeated unsupported claims, and does not reject a candidate merely for one niche knowledge gap when broader competence is well supported.

## `final_output.txt`

Used only for mechanically constrained `PROGRESS` or `NOT_PROGRESS` output.

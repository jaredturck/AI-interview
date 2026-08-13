# Prompt design

The live interviewer prompt is intentionally short. Its job is to gather useful technical information through an adaptive conversation, not to perform safety classification or candidate evaluation.

The job description is appended to the live system context on every generation. Relevant company BM25 retrieval is appended only when it matches the latest candidate turn. Rephrase, redirect, safety and closing instructions are temporary turn-specific additions rather than permanent prompt bulk.

The content guard is external to the interviewer prompt and checks both candidate input and generated interviewer output.

The misuse monitor is a separate model with a narrow `CONTINUE` / `REDIRECT` / `TERMINATE` choice. It is deliberately forgiving: unusual communication, isolated tangents or confusion should not by themselves end an interview.

The final evaluator does not receive the whole rubric as a single reasoning request. Every line in `config/evaluation_questions.txt` becomes a separate reasoning pass over the same job description and complete transcript. The concise criterion assessments then feed a separate synthesis pass.

The final choice prompt is intentionally small. Output validity is enforced in code by constrained decoding to `PROGRESS` or `NOT_PROGRESS`, so the prompt does not need formatting examples or a large output contract.

All evaluator prompts explicitly treat transcript text as candidate interview content rather than instructions to the evaluator.

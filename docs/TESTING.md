# Testing

Run from the repository root:

```bash
npm test
```

This executes Django checks, migration drift checks, pytest and a production TypeScript/Vite build. Backend tests inject `FakeModelSuite`; production has no mock-model mode.

## Required coverage

| Area | Cases |
| --- | --- |
| Ownership | HTTP/WebSocket authentication, cross-account rejection. |
| Interview policy | Opening, normal follow-up, safety redirect, misuse termination, manual end. |
| Voice turn-taking | Non-speech discard, incomplete pause hold, resumed speech, accumulated-turn completion, push-to-talk explicit submit. |
| Transcript UI | Candidate sending indicator, interviewer typing indicator, replacement by real messages. |
| Evaluation | Criterion persistence, binary result, failure state, human review. |
| Data | Immutable job snapshot, candidate data deletion/download paths. |

## Target-host checks

Automated tests do not validate real CUDA execution. On the dual-RTX-3090 host verify:

```text
Smart Turn session provider -> CUDAExecutionProvider device 1
Silero -> CPU
Qwen live-model device placement -> docs/MODELS.md
Qwen3.6 evaluation -> vLLM reports TP=2 and the criterion bar reaches the configured criterion count
Qwen3.6 evaluation -> both GPUs show concurrent compute and no CPU weight offload
Qwen3.6 regression set -> criterion evidence and PROGRESS / NOT_PROGRESS decisions remain materially consistent
Open microphone -> Chrome microphone indicator remains active
Cough/background noise -> no candidate message
Mid-sentence pause -> interviewer waits
Push-to-talk -> button release submits immediately
```

Turn thresholds and timing constants should be tuned from recorded usability tests rather than changed from anecdotal single samples.

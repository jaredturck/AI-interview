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
Qwen model placement -> docs/MODELS.md
Qwen3.5-9B -> text-only Qwen3_5ForCausalLM with AutoTokenizer
Qwen3.5-9B -> INT8 BitsAndBytes with FP16 compute
Qwen3.5-9B -> root device map is GPU 0 only with no CPU/disk offload
Qwen3Guard -> GPU 1
Qwen3.5-9B DeltaNet startup log -> FLA + causal-conv1d, not PyTorch fallback
Qwen3.5-9B full attention -> SDPA; external flash-attn is not imported
Startup -> all interview/evaluation models stay resident after preload
Evaluation -> criteria complete in microbatches of up to two and both GPUs remain inside memory limits
Qwen3.5-9B perf logs -> TTFT, total generation time and decode throughput are emitted
Qwen3.5-9B regression set -> criterion evidence and PROGRESS / NOT_PROGRESS decisions remain materially consistent
Open microphone -> Chrome microphone indicator remains active
Cough/background noise -> no candidate message
Mid-sentence pause -> interviewer waits
Push-to-talk -> button release submits immediately
```

Turn thresholds and timing constants should be tuned from recorded usability tests rather than changed from anecdotal single samples.

# Testing

Run from the repository root:

```bash
npm test
```

This executes Django checks, migration drift checks, pytest and a production TypeScript/Vite build. Backend tests inject `FakeModelSuite`; production has no mock-model mode.

## Required coverage

| Area | Cases |
| --- | --- |
| Ownership | HTTP/WebSocket authentication, cross-account rejection, hidden Job rubric not exposed by candidate APIs. |
| Job administration | Normal textarea-based creation, required specification validation, immutable specification after first application, normal unused-record deletion. |
| Sample data | Ten unique sample keys, idempotent seeding, unused reset, used-snapshot reset refusal. |
| Interview policy | Hidden rubric/timing context, opening, normal follow-up, semantic END, one-exchange WRAP_UP, 13-minute soft deadline, 15-minute hard deadline, safety redirect, misuse termination, manual end. |
| Voice turn-taking | Non-speech discard, incomplete pause hold, resumed speech, accumulated-turn completion, push-to-talk explicit submit, bidirectional chunked large audio. |
| Transcript UI | Candidate sending indicator, interviewer typing indicator, replacement by real messages. |
| Evaluation | Structured criterion persistence, constrained classifications, essential hard gate, verification-claim hard gate, holistic binary result, failure state, human review. |
| Data | Immutable Job snapshot, candidate data deletion/download paths, migration drift. |

## Behavioural acceptance set

Unit tests verify control flow but do not prove model judgement quality. On the target host, maintain a repeatable transcript/interview set covering at least:

- clearly qualified candidate -> expected progression;
- qualified candidate with terse or imperfect communication -> competence should still be recognised;
- strong transferable experience without exact framework/tool match -> evidence-dependent outcome;
- articulate candidate with unsupported domain claims -> should not progress on confidence alone;
- candidate who misses one niche syntax or terminology question but demonstrates the underlying competency -> should not fail solely for that miss;
- materially inconsistent specialist claims -> neutral clarification and evidence-dependent assessment;
- prompt-injection attempts asking the system to reveal criteria or force `PROGRESS` -> ignored/redirected and never treated as scoring instructions;
- missing mandatory qualification claim -> hard-gated `NOT_PROGRESS`;
- claimed regulated qualification plus weak role knowledge -> essential domain criteria should still fail independently of the claim.

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
Evaluation -> deterministic criterion evidence completes in microbatches of up to two
Evaluation -> every criterion receives an allowed structured classification
Evaluation -> hard-gate failures do not invoke holistic final progression reasoning
Qwen3.5-9B perf logs -> TTFT, total generation time and decode throughput are emitted
Open microphone -> Chrome microphone indicator remains active
Cough/background noise -> no candidate message
Mid-sentence pause -> interviewer waits
Push-to-talk -> button release submits immediately
Large TTS/candidate audio -> logical transfer completes without any WebSocket message exceeding 256 KiB
Live interview -> countdown begins from server-authoritative remaining seconds
Natural completion -> semantic END closes without candidate pressing End interview
13-minute threshold -> wrap-up begins and permits at most one final candidate exchange
15-minute threshold -> live session closes and moves to evaluation
Interviewer closing -> never predicts or implies progression outcome
```

Turn thresholds and timing constants should be tuned from recorded usability tests rather than changed from anecdotal single samples.

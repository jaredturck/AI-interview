# Performance

## Permanently resident placement

```text
GPU 0 (24 GB)
  Qwen3.6-27B NF4 shard
  Qwen3-TTS-1.7B BF16
  Qwen3Guard-Gen-4B INT8

GPU 1 (24 GB)
  Qwen3.6-27B NF4 shard
  Qwen3-ASR-1.7B BF16
  Qwen3.5-4B misuse INT8
  Smart Turn v3.2 FP32

CPU
  Silero VAD
```

The Qwen3.6 placement ceiling is 22 GiB per GPU. It reflects the usable capacity of each 24 GiB RTX 3090 while leaving roughly 2 GiB outside the shared-model placement budget. It is an upper limit only; the balanced text-only NF4 model is expected to occupy substantially less than 22 GiB on either card.

These are placement limits, not claims about exact CUDA peaks. Actual free/allocated/reserved memory must be measured on the target host because PyTorch, ONNX Runtime and qwentts.cpp use separate CUDA allocators.

## Shared Qwen3.6 execution

Qwen3.6 serves both live interviewing and final evaluation. This removes the previous evaluator cold-load cycle entirely.

```text
Interview turn
  -> Qwen3.6 resident model

Final evaluation
  -> criterion microbatches of 2
  -> final reasoning
  -> constrained binary decision
```

Transformers/Accelerate model placement splits whole modules across the two GPUs; it is not vLLM-style tensor parallelism. The benefit of this design is permanent residency and a much simpler inference stack rather than maximum multi-request serving throughput.

## Attention

Transformers models explicitly use `attn_implementation='sdpa'`. No external `flash-attn` binary is required. PyTorch SDPA selects an available attention kernel for the installed hardware/runtime and avoids binding the project to a separate FlashAttention C++/CUDA ABI.

## Evaluation memory controls

| Setting | Value | Purpose |
| --- | --- | --- |
| Qwen3.6 weights | BitsAndBytes NF4 4-bit | Makes the 27B shared model resident beside the realtime models. |
| Compute dtype | BF16 | Keeps matrix computation and activations at an appropriate Ampere-supported precision. |
| Nested quantization | Enabled | Reduces 4-bit quantization metadata overhead. |
| Shared-model placement ceiling | 22 GiB per GPU | Gives Accelerate a realistic per-card limit while leaving roughly 2 GiB outside the placement budget. |
| Criterion microbatch | 2 | Bounds simultaneous KV/activation growth during evaluation. |
| Active inference | Serialized | Avoids interview and evaluation activation peaks overlapping. |
| CPU weight offload | Not intended | Keeps model execution on the two RTX 3090s. |

## Target-host measurements

Before treating the memory map as final, record these on the actual dual-3090 host after startup and during representative interview/evaluation calls:

- driver-level free/total memory for each GPU;
- `torch.cuda.memory_allocated()` and `memory_reserved()` for each GPU;
- peak allocated memory for an interviewer turn;
- peak allocated memory for a two-criterion evaluation batch;
- end-to-end interviewer latency and complete evaluation wall time.

Useful host-side observation:

```bash
nvidia-smi dmon -s pucm -d 1
```

## Voice latency path

```text
2 s browser pause probe
 -> ffmpeg decode
 -> Silero VAD
 -> Smart Turn
 -> 0.5 s completion grace OR ~6 s incomplete-turn hold
 -> Qwen3-ASR
 -> safety + misuse + Qwen3.6 interviewer
 -> Qwen3-TTS
```

The hold timer is conversational policy, not model latency. It exists only when Smart Turn considers a phrase incomplete.

# Performance

## Permanently resident placement

```text
GPU 0 (24 GB)
  Qwen3.6-27B NF4
  Qwen3-TTS-1.7B BF16

GPU 1 (24 GB)
  Qwen3-ASR-1.7B BF16
  Qwen3Guard-Gen-4B INT8
  Qwen3.5-4B misuse INT8
  Smart Turn v3.2 FP32

CPU
  Silero VAD
```

Qwen3.6 is intentionally pinned to one RTX 3090. This removes Accelerate's layer-by-layer cross-GPU dispatch and keeps Qwen matrix multiplication local to GPU 0. Qwen3-TTS shares GPU 0 because its active generation phase follows Qwen interviewer generation rather than overlapping it; it is idle during final evaluation. GPU 1 owns the remaining realtime models.

These are residency choices, not claims about exact CUDA peaks. Actual free/allocated/reserved memory must be measured on the target host because PyTorch, ONNX Runtime and qwentts.cpp use separate CUDA allocators.

## Shared Qwen3.6 execution

Qwen3.6 serves both live interviewing and final evaluation. This removes the previous evaluator cold-load cycle entirely.

```text
Interview turn
  -> Qwen3.6 resident model

Final evaluation
  -> criterion microbatches of 4
  -> final reasoning
  -> constrained binary decision
```

The shared model is no longer sharded. Interview generation is batch 1 for latency; evaluation uses batches of up to four independent criteria to give the GPU larger matrix workloads and improve throughput.

## Attention and DeltaNet kernels

Qwen3.6 is a 3:1 hybrid model: 48 Gated DeltaNet layers and 16 full-attention layers. Full-attention layers use PyTorch SDPA. DeltaNet uses `flash-linear-attention` and `causal-conv1d` when both are installed; without both packages Transformers falls back to slower PyTorch DeltaNet operations. Startup reports either `FLA + causal-conv1d` or `PyTorch fallback`.

The external `flash-attn` package is not required. Flash Linear Attention is a different package used for the model's linear-attention delta-rule kernels.

## Evaluation memory controls

| Setting | Value | Purpose |
| --- | --- | --- |
| Qwen3.6 weights | BitsAndBytes NF4 4-bit | Makes the 27B shared model resident beside the realtime models. |
| Compute dtype | BF16 | Keeps matrix computation and activations at an appropriate Ampere-supported precision. |
| Nested quantization | Enabled | Reduces 4-bit quantization metadata overhead. |
| Shared-model placement | Entirely GPU 0 | Removes cross-GPU layer dispatch and hidden-state transfers. |
| Criterion microbatch | 4 | Increases evaluator GPU work per generation call while keeping a bounded batch. |
| DeltaNet kernels | FLA + causal-conv1d | Uses the optimized Qwen3.6 linear-attention path instead of the PyTorch fallback. |
| Active inference | Serialized | Avoids interview and evaluation activation peaks overlapping. |
| CPU weight offload | Not intended | Keeps model execution on the two RTX 3090s. |

## Target-host measurements

Before treating the memory map as final, record these on the actual dual-3090 host after startup and during representative interview/evaluation calls:

- driver-level free/total memory for each GPU;
- `torch.cuda.memory_allocated()` and `memory_reserved()` for each GPU;
- peak allocated memory for an interviewer turn;
- peak allocated memory for a four-criterion evaluation batch;
- end-to-end interviewer latency, Qwen first-token latency/decode throughput and complete evaluation wall time.

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

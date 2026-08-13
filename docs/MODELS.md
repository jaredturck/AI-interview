# Models

The model stack is fixed in `backend/interviews/services/real_models.py`; model IDs, placement and precision are implementation choices rather than candidate/runtime settings.

| Purpose | Model | GPU | Precision |
| --- | --- | --- | --- |
| Speech recognition | `Qwen/Qwen3-ASR-1.7B-hf` | cuda:1 | BF16 |
| Interviewer + job metadata | `Qwen/Qwen3.5-9B` | cuda:0 | INT8 |
| Text-to-speech | `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` | cuda:0 | BF16 |
| Content safety | `Qwen/Qwen3Guard-Gen-4B` | cuda:1 | INT8 |
| Misuse monitoring | `Qwen/Qwen3.5-4B` | cuda:1 | INT8 |
| Final evaluator | `Qwen/Qwen3.6-27B` | cuda:0 + cuda:1 | INT8 |

The interviewer and misuse monitor run without extended thinking. Qwen3.6 uses thinking for each criterion assessment and the final synthesis. Staff job creation reuses the resident 9B interviewer model for one short JSON metadata extraction; it does not rewrite the authored Job description.

## Loading lifecycle

Heavy model imports are delayed behind `ModelRuntime`. Django development `runserver` preloads the live stack in its serving child process, while another ASGI serving process can load it on the first interview reservation. The live stack remains resident across ordinary unfinished disconnects. Evaluation unloads it, gives both GPUs to Qwen3.6-27B, then eagerly restores the live stack when evaluation finishes.

Normal migrations/tests do not intentionally allocate the real Qwen suite; tests replace the runtime suite with deterministic fakes.

## Speech dependency compatibility

Native Hugging Face Qwen3-ASR support requires the newer Transformers line while the current Qwen3-TTS package pins an older exact version. The repository therefore installs Qwen TTS with `--no-deps` and carries the documented compatibility patch under `docs/patch_qwen_tts_transformers5.sh`. Revalidate this workaround whenever upstream Qwen TTS changes.

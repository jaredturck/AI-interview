# Models

## Realtime models

| Purpose | Model | Target | Precision |
| --- | --- | --- | --- |
| Speech recognition | Qwen/Qwen3-ASR-1.7B | cuda:1 | BF16 |
| Interviewer | Qwen/Qwen3.5-9B | cuda:0 | INT8 |
| Text-to-speech | Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice | cuda:0 | BF16 |
| Content safety | Qwen/Qwen3Guard-Gen-4B | cuda:1 | INT8 |
| Misuse monitoring | Qwen/Qwen3.5-4B | cuda:1 | INT8 |

The interviewer and misuse model run with thinking disabled to keep realtime latency low.

Qwen3-ASR uses Qwen's official `qwen-asr` package with its Hugging Face Transformers backend. Qwen3-TTS uses Qwen's official `qwen-tts` wrapper.

## Final evaluator

`Qwen/Qwen3.6-27B` runs in INT8 with thinking enabled after the live interview has finished. The evaluator receives both RTX 3090 GPUs.

Evaluation is deliberately multi-pass:

1. one extended reasoning pass for every configured evaluation question;
2. one synthesis pass across the criterion assessments;
3. one fresh final-decision reasoning pass;
4. one constrained decoding pass returning `PROGRESS` or `NOT_PROGRESS`.

The constrained output prevents application logic from depending on free-form parsing.

## Loading lifecycle

Mock mode loads no real weights.

Real mode loads the live suite before the interview worker is used. When evaluation begins the live suite is released before the 27B evaluator is loaded. The live suite is restored after evaluation finishes.

## Qwen speech dependency compatibility

`qwen-asr` 0.0.6 pins Transformers 4.57.6 and `qwen-tts` 0.1.1 pins Transformers 4.57.3. The project uses Transformers 4.57.6 because the ASR package and the Qwen3.5/Qwen3.6 model family run on that Transformers generation. Install `qwen-tts==0.1.1` with `--no-deps` after the root requirements so its narrower package metadata does not downgrade the shared runtime.

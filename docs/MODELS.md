# Models

The model stack is fixed in `backend/interviews/services/real_models.py`. Model IDs, placement and precision are implementation choices rather than runtime configuration.

| Purpose | Model | GPU | Precision |
| --- | --- | --- | --- |
| Speech recognition | `Qwen/Qwen3-ASR-1.7B-hf` | cuda:1 | BF16 |
| Interviewer | `Qwen/Qwen3.5-9B` | cuda:0 | INT8 |
| Text-to-speech | `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` | cuda:0 | BF16 |
| Content safety | `Qwen/Qwen3Guard-Gen-4B` | cuda:1 | INT8 |
| Misuse monitoring | `Qwen/Qwen3.5-4B` | cuda:1 | INT8 |
| Final evaluator | `Qwen/Qwen3.6-27B` | cuda:0 + cuda:1 | INT8 |

The interviewer and misuse monitor run without extended thinking. Qwen3.6-27B uses thinking for each criterion assessment and for the final synthesis decision.

## Loading lifecycle

Heavy model imports and allocations are lazy so normal Django startup, migrations, admin pages and application tests do not allocate GPU models.

The first live interview loads the ASR, interviewer, TTS, guard and misuse models. They remain resident after an unfinished network disconnect so a later interview or resumed interview does not have to reload them.

Final evaluation unloads the live stack and gives both GPUs to Qwen3.6-27B. After evaluation, the evaluator is unloaded and the runtime returns to idle. Live models are not eagerly reloaded until another interview needs them.

## Speech dependency compatibility

Native Hugging Face support for `Qwen/Qwen3-ASR-1.7B-hf` starts with Transformers 5.13. The current Qwen3-TTS package declares an exact Transformers 4.57.3 dependency in its package metadata.

The project therefore uses Transformers 5.13+ for the native ASR and text-model runtime and installs `qwen-tts` with `--no-deps`. Its required direct runtime packages are included in the root `requirements.txt`.

This is an upstream packaging compatibility issue rather than application configurability. Validate the real TTS import/inference path on the target machine and recheck the workaround when Qwen publishes a newer TTS package.

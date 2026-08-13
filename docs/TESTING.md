# Testing and validation

## Automated test design

Backend tests use `MockModelSuite`, so normal application logic can be tested without downloading Qwen weights.

Coverage includes:

- normal adaptive interviewer turn generation;
- immediate unsafe-turn redirection;
- isolated off-topic misuse redirect without termination;
- repeated misuse termination;
- final binary evaluator output;
- interview session access tokens;
- candidate review request submission;
- authenticated WebSocket startup and typed conversation flow.

Run everything available locally with:

```bash
./scripts/check.sh
```

## Validation performed when this repository was generated

The generation environment did not allow installing project packages from the internet, so Django/pytest and the Vite production build could not be executed there.

The following checks were executed successfully:

- Python `compileall` across the backend;
- AST parsing of every project Python file;
- TOML parsing and required runtime-model validation;
- prompt/job/rubric presence checks;
- Bash syntax validation for project scripts;
- JavaScript syntax checks for non-JSX modules;
- JSX/React parsing through the available TypeScript compiler, with only expected missing-module/type errors because `node_modules` was unavailable;
- ZIP integrity testing after packaging.

The real Qwen weights were not available in the generation environment. Their adapter APIs were cross-checked against current official Qwen/Hugging Face usage, but the actual dual-3090 runtime still requires hardware validation.

## Required first-run validation on the target workstation

After `./scripts/setup_dev.sh`:

```bash
./scripts/check.sh
```

Then manually verify in mock mode:

1. start an interview by voice;
2. start another by typed text;
3. enable transcript confirmation and edit an ASR turn;
4. replay/rephrase a question;
5. pause during a spoken answer for an extended period before pressing Finish speaking;
6. mute interviewer voice and continue from text only;
7. complete evaluation and submit a review request.

After switching to real mode, record:

- model load time;
- idle and peak VRAM on both GPUs;
- ASR latency versus utterance duration;
- interviewer time-to-first-response;
- TTS generation latency;
- evaluator criterion/synthesis duration;
- evaluator stability across a representative labelled test set.

Do not deploy to real applicants until the real-model and accessibility tests have been completed.

import ast
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message):
    print(f"ERROR: {message}")
    return 1


def main():
    errors = 0

    runtime_path = ROOT / "config" / "runtime.example.toml"
    with runtime_path.open("rb") as file:
        runtime = tomllib.load(file)

    required_models = [
        "interviewer_model",
        "misuse_model",
        "guard_model",
        "asr_model",
        "tts_model",
        "evaluator_model",
    ]
    for key in required_models:
        if not runtime["models"].get(key):
            errors += fail(f"Missing model setting: {key}")

    questions = [
        line.strip()
        for line in (ROOT / "config" / "evaluation_questions.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(questions) < 5:
        errors += fail("Evaluation rubric is unexpectedly short.")

    prompt_names = [
        "interviewer.txt",
        "misuse.txt",
        "evaluator_question.txt",
        "evaluator_synthesis.txt",
        "final_choice.txt",
    ]
    for name in prompt_names:
        if not (ROOT / "prompts" / name).read_text(encoding="utf-8").strip():
            errors += fail(f"Prompt is empty: {name}")

    if not (ROOT / "config" / "job_description.md").read_text(encoding="utf-8").strip():
        errors += fail("Job description is empty.")

    for path in (ROOT / "backend").rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    for dependency in ["react", "react-dom", "vite", "tailwindcss"]:
        if dependency not in package["dependencies"]:
            errors += fail(f"Missing frontend dependency: {dependency}")

    if errors:
        return 1

    print(f"Static validation passed: {len(questions)} evaluation questions, {len(prompt_names)} prompts, Python syntax valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

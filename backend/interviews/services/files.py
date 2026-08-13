from pathlib import Path

from ai_interviewer.runtime_config import RUNTIME

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROMPT_ROOT = PROJECT_ROOT / "prompts"


def read_prompt(name):
    return (PROMPT_ROOT / name).read_text(encoding="utf-8").strip()


INTERVIEWER_PROMPT = read_prompt("interviewer.txt")
MISUSE_PROMPT = read_prompt("misuse.txt")
EVALUATOR_QUESTION_PROMPT = read_prompt("evaluator_question.txt")
EVALUATOR_SYNTHESIS_PROMPT = read_prompt("evaluator_synthesis.txt")
FINAL_CHOICE_PROMPT = read_prompt("final_choice.txt")

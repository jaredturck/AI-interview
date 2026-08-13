''' Load staff-authored job configuration and model prompts from editable project files. '''

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_ROOT = PROJECT_ROOT / 'config'
PROMPT_ROOT = PROJECT_ROOT / 'prompts'
JOB_DESCRIPTION_PATH = CONFIG_ROOT / 'job_description.md'
EVALUATION_QUESTIONS_PATH = CONFIG_ROOT / 'evaluation_questions.txt'

def read_text(path):
    ''' Centralize trimmed UTF-8 reads for project-managed prompt and configuration content. '''
    return path.read_text(encoding='utf-8').strip()

def read_prompt(name):
    ''' Resolve a named model prompt from the project prompts directory. '''
    return read_text(PROMPT_ROOT / name)

def get_job_configuration():
    ''' Return the exact staff-authored description and evaluation rubric used when creating a new job. '''
    return read_text(JOB_DESCRIPTION_PATH), read_text(EVALUATION_QUESTIONS_PATH)

def parse_evaluation_questions(text):
    ''' Convert a stored evaluation rubric into ordered non-empty criterion lines. '''
    questions = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if line:
            questions.append(line)

    return questions

INTERVIEWER_PROMPT = read_prompt('interviewer.txt')
MISUSE_PROMPT = read_prompt('misuse.txt')
EVALUATOR_QUESTION_PROMPT = read_prompt('evaluator_question.txt')
FINAL_CHOICE_PROMPT = read_prompt('final_choice.txt')
FINAL_OUTPUT_PROMPT = read_prompt('final_output.txt')

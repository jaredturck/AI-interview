''' Load the job description, evaluation rubric and model prompts from editable project files. '''

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

def get_job_description():
    ''' Supply the job description shared by live interviewing and final evaluation. '''
    return read_text(JOB_DESCRIPTION_PATH)

def get_job_title():
    ''' Extract the role title shown in the UI from the job description heading. '''
    for raw_line in get_job_description().splitlines():
        line = raw_line.strip()

        if line.startswith('# '):
            return line[2:].strip()

    return 'Technical role'

def get_evaluation_questions():
    ''' Load the ordered criteria that drive separate Qwen3.6 evaluation passes. '''
    questions = []

    for raw_line in read_text(EVALUATION_QUESTIONS_PATH).splitlines():
        line = raw_line.strip()

        if line:
            questions.append(line)

    return questions

INTERVIEWER_PROMPT = read_prompt('interviewer.txt')
MISUSE_PROMPT = read_prompt('misuse.txt')
EVALUATOR_QUESTION_PROMPT = read_prompt('evaluator_question.txt')
FINAL_CHOICE_PROMPT = read_prompt('final_choice.txt')
FINAL_OUTPUT_PROMPT = read_prompt('final_output.txt')

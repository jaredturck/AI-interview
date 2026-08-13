''' Load prompts and editable interview content from project files. '''

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_ROOT = PROJECT_ROOT / 'config'
PROMPT_ROOT = PROJECT_ROOT / 'prompts'
JOB_DESCRIPTION_PATH = CONFIG_ROOT / 'job_description.md'
EVALUATION_QUESTIONS_PATH = CONFIG_ROOT / 'evaluation_questions.txt'

def read_text(path):
    ''' Read a UTF-8 project text file. '''
    return path.read_text(encoding='utf-8').strip()

def read_prompt(name):
    ''' Read one prompt file. '''
    return read_text(PROMPT_ROOT / name)

def get_job_description():
    ''' Return the configured job description. '''
    return read_text(JOB_DESCRIPTION_PATH)

def get_job_title():
    ''' Return the role title from the job description heading. '''
    for raw_line in get_job_description().splitlines():
        line = raw_line.strip()

        if line.startswith('# '):
            return line[2:].strip()

    return 'Technical role'

def get_evaluation_questions():
    ''' Return the configured post-interview evaluation questions. '''
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

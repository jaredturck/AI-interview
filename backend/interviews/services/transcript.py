''' Shape stored interview evidence for Qwen3.5-9B live context, misuse monitoring and final evaluation. '''

def turn_list(interview):
    ''' Shape stored transcript turns into the role and text history expected by the Qwen3.5-9B interviewer. '''
    return list(interview.turns.values('role', 'text'))

def transcript_text(interview):
    ''' Format the full transcript as labeled text for misuse monitoring and Qwen3.5-9B final evaluation. '''
    lines = []

    for turn in interview.turns.all():
        speaker = 'Candidate' if turn.role == 'user' else 'Interviewer'
        lines.append(f'{speaker}: {turn.text}')

    return '\n\n'.join(lines)

''' Format stored interview turns for live prompts and final evaluation. '''

def turn_list(interview):
    ''' Return ordered role and text dictionaries for the live interviewer. '''
    return list(interview.turns.values('role', 'text'))

def transcript_text(interview):
    ''' Return the complete interview as readable plain text. '''
    lines = []

    for turn in interview.turns.all():
        speaker = 'Candidate' if turn.role == 'user' else 'Interviewer'
        lines.append(f'{speaker}: {turn.text}')

    return '\n\n'.join(lines)

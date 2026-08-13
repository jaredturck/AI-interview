def turn_list(interview):
    return list(interview.turns.values("role", "text"))


def transcript_text(interview):
    lines = []
    for turn in interview.turns.all():
        speaker = "Candidate" if turn.role == "user" else "Interviewer"
        lines.append(f"{speaker}: {turn.text}")
    return "\n\n".join(lines)

# Future work

- Design company knowledge/RAG as a separate subsystem: authoritative sources, freshness, permissions, retrieval quality and prompt-injection boundaries.
- Add true full-duplex barge-in so candidate speech can cancel interviewer generation/TTS after a turn has already been committed.
- Measure real interview turn-taking data and tune RMS, Silero, Smart Turn and hold/grace thresholds from observed false accepts/rejects.
- Profile live inference before changing batching, model sizes, quantization or GPU placement.

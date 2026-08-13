# Security

## Authentication, CSRF and ownership

Candidates use Django password hashing and server-side sessions. `JobApplication.user` is the ownership boundary for application and interview resources.

All candidate job/application/interview endpoints requiring account data verify authentication and ownership. State-changing HTTP calls remain protected by Django CSRF middleware; the React API client sends the CSRF cookie value as `X-CSRFToken`. Channels uses `AuthMiddlewareStack`, and every interview WebSocket verifies ownership before accepting model work.

`AllowedHostsOriginValidator` restricts authenticated WebSocket origins. Production must also configure allowed hosts and trusted CSRF origins correctly.

## Rendering and injection safety

Candidate APIs return JSON only. React renders job metadata, descriptions, transcript text and model output as normal escaped text; the application does not use `dangerouslySetInnerHTML` for candidate/model content. Django admin templates retain Django autoescaping. ORM queries use Django query APIs rather than interpolated SQL.

The custom staff job-creation form is protected by Django admin authentication and CSRF. AI-derived job metadata is stored as plain text and never treated as HTML.

## AI and resource safety

Candidate text is checked by Qwen3Guard before interviewer generation, and generated interviewer text is checked again before TTS. A separate misuse model can redirect or terminate the conversation but cannot decide the hiring outcome.

Resource limits include capped candidate text, 20 MB WebSocket audio, bounded ffmpeg decoding, a 60-second decoder timeout, a 30-minute interview limit and exclusive GPU-worker ownership.

## Failure behaviour

Evaluation failures never create a positive/negative candidate result. They become `evaluation_failed`, after which human review can be requested. A stale in-process evaluation after backend restart is converted to explicit failure instead of leaving the application indefinitely pending.

## Production requirements

Before public deployment use TLS, strong secrets, production host/origin settings, endpoint rate limiting, dependency/OS patching, monitoring and an explicit candidate data retention/privacy policy. Automated-decision and recruitment notices should be reviewed with appropriate legal/data-protection specialists for the deployment jurisdiction.

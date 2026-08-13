export type ApplicationStatus = 'interview_pending' | 'interview_in_progress' | 'evaluating' | 'complete' | 'withdrawn';
export type InterviewStatus = 'created' | 'active' | 'completed' | 'terminated' | 'evaluating' | 'evaluated' | 'evaluation_failed';
export type InterviewResult = '' | 'PROGRESS' | 'NOT_PROGRESS';
export type LiveStatus = 'idle' | 'connecting' | 'loading' | 'ready' | 'listening' | 'transcribing' | 'confirming' | 'thinking' | 'speaking' | 'paused' | 'complete' | 'evaluation_failed';
export type TranscriptRole = 'assistant' | 'user';

export interface AuthStatus {
    authenticated: boolean;
    email?: string;
}

export interface BootstrapData {
    max_minutes: number;
    recruitment_email: string;
}

export interface InterviewSummary {
    id: string;
    status: InterviewStatus;
    result: InterviewResult;
    created_at: string;
    started_at: string | null;
    ended_at: string | null;
    review_requested: boolean;
}

export interface ApplicationSummary {
    id: string;
    status: ApplicationStatus;
    applied_at: string;
    interview: InterviewSummary | null;
}

export interface JobSummary {
    id: string;
    title: string;
    subtitle: string;
    status: 'open' | 'closed';
    opened_at: string | null;
    description_excerpt?: string;
    description?: string;
    application: ApplicationSummary | null;
}

export interface JobApplication extends ApplicationSummary {
    job: JobSummary;
}

export interface AccountData {
    email: string;
    applications: JobApplication[];
}

export interface InterviewStatusResponse {
    interview: InterviewSummary;
    application: {
        id: string;
        status: ApplicationStatus;
    };
    job: JobSummary;
}

export interface TranscriptMessage {
    id: string;
    role: TranscriptRole;
    text: string;
}

export interface TranscriptTurn {
    role: TranscriptRole;
    text: string;
}

export interface WebSocketErrorMessage {
    type: 'error';
    code?: string;
    message: string;
}

export type WebSocketMessage =
    | {type: 'history'; turns: TranscriptTurn[]}
    | {type: 'ready'}
    | {type: 'status'; status: LiveStatus}
    | {type: 'candidate'; text: string}
    | {type: 'assistant'; text: string}
    | {type: 'transcription'; text: string; requires_confirmation: boolean}
    | {type: 'ended'; status?: InterviewStatus; result?: InterviewResult}
    | {type: 'audio_unavailable'}
    | WebSocketErrorMessage;

export interface StartInterviewPayload {
    confirm_transcript: boolean;
}

export interface StartInterviewResponse {
    interview: InterviewSummary;
    job: JobSummary;
}

import i18n from './i18n';
import type { AccountData, AuthStatus, BootstrapData, InterviewStatusResponse, JobApplication, JobSummary, StartInterviewPayload, StartInterviewResponse } from './types';

export class ApiError extends Error {
    code: string;

    constructor(message: string, code = '') {
        super(message);
        this.name = 'ApiError';
        this.code = code;
    }
}

function cookie(name: string) {
    const item = document.cookie.split('; ').find((part) => part.startsWith(`${name}=`));
    return item ? decodeURIComponent(item.split('=')[1]) : '';
}

async function request<T>(url: string, options: RequestInit = {}) {
    const headers = new Headers(options.headers);
    headers.set('Content-Type', 'application/json');
    headers.set('Accept-Language', i18n.resolvedLanguage || i18n.language || 'en');

    if (options.method && options.method !== 'GET') {
        headers.set('X-CSRFToken', cookie('csrftoken'));
    }

    const response = await fetch(url, {credentials: 'same-origin', ...options, headers});
    const data = await response.json();

    if (!response.ok) {
        throw new ApiError(data.error || i18n.t('errors.request'), data.code || '');
    }

    return data as T;
}

export function get_auth_status() {
    return request<AuthStatus>('/api/auth/status/');
}

export function signup(email: string, password: string) {
    return request<AuthStatus>('/api/auth/signup/', {method: 'POST', body: JSON.stringify({email, password})});
}

export function login(email: string, password: string) {
    return request<AuthStatus>('/api/auth/login/', {method: 'POST', body: JSON.stringify({email, password})});
}

export function logout() {
    return request<AuthStatus>('/api/auth/logout/', {method: 'POST'});
}

export function get_bootstrap() {
    return request<BootstrapData>('/api/bootstrap/');
}

export function get_jobs() {
    return request<{jobs: JobSummary[]}>('/api/jobs/');
}

export function get_job(job_id: string) {
    return request<{job: JobSummary}>(`/api/jobs/${job_id}/`);
}

export function apply_job(job_id: string) {
    return request<{application: JobApplication}>(`/api/jobs/${job_id}/apply/`, {method: 'POST'});
}

export function get_account() {
    return request<AccountData>('/api/account/');
}

export function get_application(application_id: string) {
    return request<{application: JobApplication}>(`/api/applications/${application_id}/`);
}

export function delete_interview_data(interview_id: string) {
    return request<{deleted: boolean}>(`/api/interviews/${interview_id}/delete/`, {method: 'POST'});
}

export function delete_all_interview_data() {
    return request<{deleted: boolean}>('/api/account/interview-data/delete/', {method: 'POST'});
}

export function start_application_interview(application_id: string, payload: StartInterviewPayload) {
    return request<StartInterviewResponse>(`/api/applications/${application_id}/interview/start/`, {method: 'POST', body: JSON.stringify(payload)});
}

export function get_interview_status(interview_id: string) {
    return request<InterviewStatusResponse>(`/api/interviews/${interview_id}/status/`);
}

export function submit_review(interview_id: string, explanation: string) {
    return request<{review_id: number; submitted: boolean}>(`/api/interviews/${interview_id}/review/`, {method: 'POST', body: JSON.stringify({explanation})});
}

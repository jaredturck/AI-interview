function cookie(name) {
    const item = document.cookie.split('; ').find((part) => part.startsWith(`${name}=`));
    return item ? decodeURIComponent(item.split('=')[1]) : '';
}

async function request(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (options.method && options.method !== 'GET') {
        headers['X-CSRFToken'] = cookie('csrftoken');
    }

    const response = await fetch(url, {
        credentials: 'same-origin',
        ...options,
        headers,
    });
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || 'The request failed.');
    }

    return data;
}

export function get_auth_status() {
    return request('/api/auth/status/');
}

export function signup(email, password) {
    return request('/api/auth/signup/', {method: 'POST', body: JSON.stringify({email, password})});
}

export function login(email, password) {
    return request('/api/auth/login/', {method: 'POST', body: JSON.stringify({email, password})});
}

export function logout() {
    return request('/api/auth/logout/', {method: 'POST'});
}

export function get_account() {
    return request('/api/account/');
}

export function get_bootstrap() {
    return request('/api/bootstrap/');
}

export function start_interview(payload) {
    return request('/api/interviews/start/', {method: 'POST', body: JSON.stringify(payload)});
}

export function get_interview_status(interview_id) {
    return request(`/api/interviews/${interview_id}/status/`);
}

export function submit_review(interview_id, explanation) {
    return request(`/api/interviews/${interview_id}/review/`, {method: 'POST', body: JSON.stringify({explanation})});
}

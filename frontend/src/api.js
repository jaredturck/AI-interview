function cookie(name) {
    const item = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
    return item ? decodeURIComponent(item.split("=")[1]) : "";
}

async function request(url, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...options.headers,
    };

    if (options.method && options.method !== "GET") {
        headers["X-CSRFToken"] = cookie("csrftoken");
    }

    const response = await fetch(url, {
        credentials: "same-origin",
        ...options,
        headers,
    });
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "The request failed.");
    }

    return data;
}

export function get_bootstrap() {
    return request("/api/bootstrap/");
}

export function start_interview(payload) {
    return request("/api/interviews/start/", {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

export function get_interview_status(interview_id, token) {
    return request(`/api/interviews/${interview_id}/status/`, {
        headers: {"X-Interview-Token": token},
    });
}

export function submit_review(interview_id, token, payload) {
    return request(`/api/interviews/${interview_id}/review/`, {
        method: "POST",
        headers: {"X-Interview-Token": token},
        body: JSON.stringify(payload),
    });
}

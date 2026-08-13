import { useState } from "react";

import { submit_review } from "../api";

export default function ReviewForm({session}) {
    const [open, set_open] = useState(false);
    const [name, set_name] = useState("");
    const [email, set_email] = useState("");
    const [explanation, set_explanation] = useState("");
    const [submitted, set_submitted] = useState(false);
    const [error, set_error] = useState("");

    function submit(event) {
        event.preventDefault();
        set_error("");
        submit_review(session.interview_id, session.access_token, {name, email, explanation})
            .then(() => set_submitted(true))
            .catch((caught) => set_error(caught.message));
    }

    if (submitted) {
        return <div className="mt-6 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4 text-emerald-100">Your request for human review has been submitted.</div>;
    }

    if (!open) {
        return <button onClick={() => set_open(true)} className="mt-6 min-h-11 rounded-xl border border-slate-600 px-4 font-medium text-slate-100 hover:bg-white/5">Request a human review</button>;
    }

    return (
        <form onSubmit={submit} className="mt-6 rounded-2xl border border-white/10 bg-slate-900 p-5 text-left">
            <h2 className="text-lg font-semibold">Request a human review</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">If you believe the automated interview or decision did not fairly reflect your experience, explain what happened and a person can reconsider it.</p>
            <label htmlFor="review-name" className="mt-4 block text-sm font-medium">Name</label>
            <input id="review-name" required value={name} onChange={(event) => set_name(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-slate-700 bg-slate-950 px-3" />
            <label htmlFor="review-email" className="mt-4 block text-sm font-medium">Email</label>
            <input id="review-email" required type="email" value={email} onChange={(event) => set_email(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-slate-700 bg-slate-950 px-3" />
            <label htmlFor="review-explanation" className="mt-4 block text-sm font-medium">What should we review?</label>
            <textarea id="review-explanation" required value={explanation} onChange={(event) => set_explanation(event.target.value)} rows="5" className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 p-3" />
            {error && <div role="alert" className="mt-3 text-sm text-red-300">{error}</div>}
            <button className="mt-4 min-h-11 rounded-xl bg-blue-500 px-4 font-semibold hover:bg-blue-400">Submit review request</button>
        </form>
    );
}

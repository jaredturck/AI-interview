import { useState } from "react";

export default function SetupScreen({bootstrap, on_start, error}) {
    const [name, set_name] = useState("");
    const [email, set_email] = useState("");
    const [language, set_language] = useState("English");
    const [confirm_transcript, set_confirm_transcript] = useState(bootstrap.review_transcript_default);
    const [mic_status, set_mic_status] = useState("Not tested");
    const [starting, set_starting] = useState(false);

    function test_microphone() {
        set_mic_status("Checking…");
        navigator.mediaDevices.getUserMedia({audio: true}).then((stream) => {
            stream.getTracks().forEach((track) => track.stop());
            set_mic_status("Microphone ready");
        }).catch(() => set_mic_status("Microphone unavailable — you can still type"));
    }

    async function submit(event) {
        event.preventDefault();
        set_starting(true);
        await on_start({
            job_id: bootstrap.job.id,
            name,
            email,
            language,
            confirm_transcript,
        });
        set_starting(false);
    }

    return (
        <main className="mx-auto flex min-h-screen max-w-5xl items-center px-4 py-10 sm:px-6">
            <section className="grid w-full gap-8 lg:grid-cols-[1.1fr_0.9fr]">
                <div className="flex flex-col justify-center">
                    <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-blue-300">Stage-one interview</p>
                    <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">A technical conversation, not a questionnaire.</h1>
                    <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-300">
                        You can answer by voice, by typing, or switch between both. The interviewer will adapt its questions to the conversation and show every question as text as well as speaking it aloud.
                    </p>
                    <div className="mt-7 grid gap-3 text-sm text-slate-300 sm:grid-cols-2">
                        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">Ask for a question to be rephrased at any time.</div>
                        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">Pause whenever you need more time to think.</div>
                        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">Review speech transcription before sending if you prefer.</div>
                        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">A human review can be requested after the interview.</div>
                    </div>
                </div>

                <form onSubmit={submit} className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/30 backdrop-blur sm:p-8">
                    <h2 className="text-2xl font-semibold text-white">Interview setup</h2>
                    <p className="mt-2 text-sm leading-6 text-slate-400">This stage uses AI to conduct the conversation and make the initial progression decision. The interview can last up to {bootstrap.max_minutes} minutes.</p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">Your text transcript is stored for assessment and review. Microphone audio is processed for transcription and is not stored by this application.</p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">If you need a different adjustment before starting, contact <a className="text-blue-300 underline underline-offset-2" href={`mailto:${bootstrap.recruitment_email}`}>{bootstrap.recruitment_email}</a>.</p>

                    <label className="mt-6 block text-sm font-medium text-slate-200" htmlFor="name">Name <span className="text-slate-500">(optional)</span></label>
                    <input id="name" value={name} onChange={(event) => set_name(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 text-white" autoComplete="name" />

                    <label className="mt-4 block text-sm font-medium text-slate-200" htmlFor="email">Email <span className="text-slate-500">(optional)</span></label>
                    <input id="email" type="email" value={email} onChange={(event) => set_email(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 text-white" autoComplete="email" />

                    <label className="mt-4 block text-sm font-medium text-slate-200" htmlFor="language">Interview language</label>
                    <select id="language" value={language} onChange={(event) => set_language(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 text-white">
                        {bootstrap.languages.map((item) => <option key={item}>{item}</option>)}
                    </select>

                    <label className="mt-5 flex cursor-pointer gap-3 rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                        <input type="checkbox" checked={confirm_transcript} onChange={(event) => set_confirm_transcript(event.target.checked)} className="mt-1 h-5 w-5" />
                        <span>
                            <span className="block font-medium text-slate-100">Review voice transcription before sending</span>
                            <span className="mt-1 block text-sm leading-5 text-slate-400">Useful if speech recognition often mishears you. You can edit the transcript before the interviewer sees it.</span>
                        </span>
                    </label>

                    <div className="mt-5 flex items-center justify-between gap-3 rounded-xl border border-slate-800 p-4">
                        <div>
                            <div className="font-medium text-slate-100">Microphone</div>
                            <div className="mt-1 text-sm text-slate-400">{mic_status}</div>
                        </div>
                        <button type="button" onClick={test_microphone} className="min-h-11 rounded-xl border border-slate-600 px-4 font-medium text-slate-100 hover:bg-white/5">Test</button>
                    </div>

                    {error && <div role="alert" className="mt-5 rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">{error}</div>}

                    <button disabled={starting || !bootstrap.capacity_available} className="mt-6 min-h-12 w-full rounded-xl bg-blue-500 px-5 font-semibold text-white hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-50">
                        {starting ? "Starting…" : bootstrap.capacity_available ? `Start ${bootstrap.job.title} interview` : "Interview worker is busy"}
                    </button>
                </form>
            </section>
        </main>
    );
}

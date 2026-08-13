function status_label(interview) {
    if (interview.result === 'PROGRESS') {
        return 'Progress';
    }

    if (interview.result === 'NOT_PROGRESS') {
        return 'Not progressing';
    }

    return interview.status.replaceAll('_', ' ');
}

export default function AccountScreen({account, on_start, on_resume, on_view, on_logout}) {
    return (
        <main className="mx-auto min-h-screen max-w-5xl px-4 py-10 text-white sm:px-6">
            <header className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-300">Candidate account</p>
                    <h1 className="mt-2 text-3xl font-semibold">Your interviews</h1>
                    <p className="mt-2 text-slate-400">Signed in as {account.email}</p>
                </div>
                <button type="button" onClick={on_logout} className="min-h-11 rounded-xl border border-slate-700 px-4 hover:bg-white/5">Sign out</button>
            </header>

            <section className="mt-8 rounded-3xl border border-white/10 bg-slate-950/70 p-5 sm:p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h2 className="text-xl font-semibold">Stage-one technical interview</h2>
                        <p className="mt-2 text-sm leading-6 text-slate-400">Your interview history and automated stage-one outcomes appear here.</p>
                    </div>
                    <button type="button" onClick={on_start} className="min-h-11 rounded-xl bg-blue-500 px-5 font-semibold hover:bg-blue-400">Start interview</button>
                </div>

                <div className="mt-6 grid gap-3">
                    {account.interviews.length === 0 && <p className="rounded-xl border border-slate-800 p-4 text-slate-400">You have not started an interview yet.</p>}
                    {account.interviews.map((interview) => {
                        const resumable = ['created', 'active'].includes(interview.status);
                        return (
                            <article key={interview.id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                                <div>
                                    <div className="font-medium capitalize">{status_label(interview)}</div>
                                    <div className="mt-1 text-sm text-slate-400">Started {new Date(interview.created_at).toLocaleString()}</div>
                                </div>
                                {resumable ? <button type="button" onClick={() => on_resume(interview.id)} className="min-h-11 rounded-xl border border-blue-400/50 px-4 text-blue-200 hover:bg-blue-500/10">Resume</button> : <button type="button" onClick={() => on_view(interview.id)} className="min-h-11 rounded-xl border border-slate-600 px-4 text-slate-200 hover:bg-white/5">View</button>}
                            </article>
                        );
                    })}
                </div>
            </section>
        </main>
    );
}

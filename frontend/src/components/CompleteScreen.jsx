import ReviewForm from "./ReviewForm";

export default function CompleteScreen({interview}) {
    const evaluated = Boolean(interview.result);
    const progressed = interview.result === "PROGRESS";
    const evaluation_failed = interview.status === "evaluation_failed";

    return (
        <main className="mx-auto flex min-h-screen max-w-2xl items-center px-4 py-10 text-white">
            <section className="w-full rounded-3xl border border-white/10 bg-slate-950/80 p-6 text-center shadow-2xl sm:p-8">
                <div aria-hidden="true" className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-blue-500/20 text-2xl">✓</div>
                <h1 className="mt-4 text-3xl font-semibold">Thank you for your time</h1>
                <div role="status" aria-live="polite">
                    {!evaluated && !evaluation_failed && <p className="mt-3 leading-7 text-slate-300">Your stage-one interview has finished and the technical evaluation is being completed.</p>}
                    {evaluation_failed && <p className="mt-3 leading-7 text-amber-200">The automated technical evaluation could not complete successfully. You can request a human review below.</p>}
                    {evaluated && progressed && <p className="mt-3 leading-7 text-slate-300">The stage-one assessment recommends progressing your application to a human interview.</p>}
                    {evaluated && !progressed && <p className="mt-3 leading-7 text-slate-300">The stage-one assessment does not recommend progressing this application to the next interview.</p>}
                </div>
                {(evaluated || evaluation_failed) && <ReviewForm session={interview.session} />}
            </section>
        </main>
    );
}

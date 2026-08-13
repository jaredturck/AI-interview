import { useEffect, useState } from "react";

export default function TranscriptConfirmation({text, on_confirm}) {
    const [value, set_value] = useState(text);

    useEffect(() => set_value(text), [text]);

    if (!text) {
        return null;
    }

    return (
        <section aria-labelledby="transcript-confirmation-title" className="border-t border-amber-300/20 bg-amber-300/10 p-4">
            <div className="mx-auto max-w-3xl">
                <h2 id="transcript-confirmation-title" className="font-semibold text-amber-100">Check what we heard</h2>
                <p className="mt-1 text-sm text-amber-100/80">Edit anything that was transcribed incorrectly, then send it to the interviewer.</p>
                <textarea aria-label="Corrected voice transcript" value={value} onChange={(event) => set_value(event.target.value)} rows="3" className="mt-3 w-full rounded-xl border border-amber-200/30 bg-slate-950 p-3 text-white" />
                <button onClick={() => on_confirm(value)} className="mt-3 min-h-11 rounded-xl bg-amber-200 px-4 font-semibold text-slate-950 hover:bg-amber-100">Use this transcript</button>
            </div>
        </section>
    );
}

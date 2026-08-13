import { useState } from "react";

export default function InterviewControls({interview}) {
    const [text, set_text] = useState("");
    const busy = ["thinking", "transcribing", "speaking", "connecting", "confirming"].includes(interview.status);

    function submit(event) {
        event.preventDefault();
        interview.send_text(text);
        set_text("");
    }

    return (
        <div className="border-t border-white/10 bg-slate-950/90 p-4 backdrop-blur">
            <div className="mx-auto max-w-4xl">
                <form onSubmit={submit} className="flex gap-2">
                    <label htmlFor="typed-response" className="sr-only">Type a response</label>
                    <textarea id="typed-response" value={text} onChange={(event) => set_text(event.target.value)} placeholder="Type a response…" rows="2" className="min-h-12 flex-1 resize-none rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white placeholder:text-slate-500" />
                    <button disabled={!text.trim() || busy} className="min-h-12 rounded-xl bg-blue-500 px-5 font-semibold text-white hover:bg-blue-400 disabled:opacity-40">Send</button>
                </form>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button disabled={busy && !interview.is_recording} onClick={interview.is_recording ? interview.stop_recording : interview.start_recording} className={`min-h-11 rounded-xl px-4 font-semibold ${interview.is_recording ? "bg-red-500 text-white" : "border border-slate-600 text-slate-100 hover:bg-white/5"}`}>
                        {interview.is_recording ? "Finish speaking" : "Speak"}
                    </button>
                    <button type="button" onClick={interview.replay} className="min-h-11 rounded-xl border border-slate-700 px-4 text-slate-200 hover:bg-white/5">Replay question</button>
                    <button type="button" disabled={busy} onClick={interview.rephrase} className="min-h-11 rounded-xl border border-slate-700 px-4 text-slate-200 hover:bg-white/5 disabled:opacity-40">Rephrase question</button>
                    <button type="button" onClick={interview.need_moment} className="min-h-11 rounded-xl border border-slate-700 px-4 text-slate-200 hover:bg-white/5">I need a moment</button>
                    <button type="button" onClick={() => interview.set_voice_enabled(!interview.voice_enabled)} className="min-h-11 rounded-xl border border-slate-700 px-4 text-slate-200 hover:bg-white/5">{interview.voice_enabled ? "Mute interviewer voice" : "Enable interviewer voice"}</button>
                    <label className="ml-auto flex min-h-11 items-center gap-2 rounded-xl border border-slate-700 px-3 text-sm text-slate-300">
                        Voice speed
                        <select value={interview.speech_speed} onChange={(event) => interview.set_speech_speed(Number(event.target.value))} className="rounded bg-slate-900 px-2 py-1 text-white">
                            <option value="0.75">0.75×</option>
                            <option value="1">1×</option>
                            <option value="1.25">1.25×</option>
                            <option value="1.5">1.5×</option>
                        </select>
                    </label>
                    <button type="button" onClick={interview.end_interview} className="min-h-11 rounded-xl border border-red-400/40 px-4 text-red-200 hover:bg-red-500/10">End interview</button>
                </div>
            </div>
        </div>
    );
}

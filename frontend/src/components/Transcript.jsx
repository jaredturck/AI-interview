import { useEffect, useRef } from "react";

export default function Transcript({messages}) {
    const end_ref = useRef(null);

    useEffect(() => {
        end_ref.current?.scrollIntoView({behavior: "auto", block: "end"});
    }, [messages]);

    return (
        <section aria-label="Interview transcript" className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
            <div className="mx-auto flex max-w-3xl flex-col gap-4">
                {messages.length === 0 && <p className="text-center text-sm text-slate-500">The transcript will appear here.</p>}
                {messages.map((message) => (
                    <article key={message.id} className={`max-w-[90%] rounded-2xl px-4 py-3 leading-7 ${message.role === "user" ? "ml-auto bg-blue-500 text-white" : "mr-auto border border-white/10 bg-slate-900 text-slate-100"}`}>
                        <div className="mb-1 text-xs font-semibold uppercase tracking-wide opacity-70">{message.role === "user" ? "You" : "Interviewer"}</div>
                        <p className="m-0 whitespace-pre-wrap">{message.text}</p>
                    </article>
                ))}
                <div ref={end_ref} />
            </div>
        </section>
    );
}

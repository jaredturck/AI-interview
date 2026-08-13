import { useEffect, useState } from "react";

import { get_bootstrap } from "./api";
import CompleteScreen from "./components/CompleteScreen";
import InterviewScreen from "./components/InterviewScreen";
import SetupScreen from "./components/SetupScreen";
import useInterview from "./hooks/useInterview";

export default function App() {
    const [bootstrap, set_bootstrap] = useState(null);
    const [error, set_error] = useState("");
    const interview = useInterview();

    useEffect(() => {
        get_bootstrap().then(set_bootstrap).catch((caught) => set_error(caught.message));
    }, []);

    useEffect(() => {
        if (!bootstrap || bootstrap.capacity_available || interview.session) {
            return undefined;
        }

        const timer = window.setInterval(() => {
            get_bootstrap().then(set_bootstrap).catch(() => {});
        }, 5000);
        return () => window.clearInterval(timer);
    }, [bootstrap, interview.session]);

    function start(payload) {
        set_error("");
        return interview.begin(payload).catch((caught) => set_error(caught.message));
    }

    if (!bootstrap) {
        return <main className="grid min-h-screen place-items-center text-slate-300">{error || "Loading interview…"}</main>;
    }

    if (!bootstrap.job) {
        return <main className="grid min-h-screen place-items-center px-4 text-center text-slate-300">There is no active interview role configured.</main>;
    }

    if (interview.ended) {
        return <CompleteScreen interview={interview} />;
    }

    if (interview.session) {
        return <InterviewScreen interview={interview} />;
    }

    return <SetupScreen bootstrap={bootstrap} on_start={start} error={error || interview.error} />;
}

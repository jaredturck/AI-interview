import { useEffect, useRef, useState } from 'react';

import { get_account, get_auth_status, get_bootstrap, login, logout, signup } from './api';
import AccountScreen from './components/AccountScreen';
import AuthScreen from './components/AuthScreen';
import CompleteScreen from './components/CompleteScreen';
import InterviewScreen from './components/InterviewScreen';
import SetupScreen from './components/SetupScreen';
import useInterview from './hooks/useInterview';

export default function App() {
    const [bootstrap, set_bootstrap] = useState(null);
    const [auth, set_auth] = useState(null);
    const [account, set_account] = useState(null);
    const [route, set_route] = useState(window.location.pathname);
    const [error, set_error] = useState('');
    const restored_ref = useRef(false);
    const interview = useInterview();

    useEffect(() => {
        Promise.all([get_bootstrap(), get_auth_status()]).then(([bootstrap_data, auth_data]) => {
            set_bootstrap(bootstrap_data);
            set_auth(auth_data);

            if (auth_data.authenticated) {
                refresh_account();
            }
        }).catch((caught) => set_error(caught.message));

        function handle_popstate() {
            set_route(window.location.pathname);
        }

        window.addEventListener('popstate', handle_popstate);
        return () => window.removeEventListener('popstate', handle_popstate);
    }, []);

    useEffect(() => {
        if (!auth?.authenticated || route !== '/interview' || interview.session || restored_ref.current || !bootstrap) {
            return;
        }

        restored_ref.current = true;
        const interview_id = sessionStorage.getItem('ai_interview_id');

        if (interview_id) {
            interview.resume(interview_id, bootstrap.job.title).catch(() => sessionStorage.removeItem('ai_interview_id'));
        }
    }, [auth, route, interview.session, bootstrap]);

    function navigate(path) {
        window.history.pushState({}, '', path);
        set_route(path);
        set_error('');
    }

    function refresh_account() {
        return get_account().then(set_account).catch((caught) => set_error(caught.message));
    }

    async function submit_auth(mode, email, password) {
        set_error('');

        try {
            const data = mode === 'signup' ? await signup(email, password) : await login(email, password);
            set_auth(data);
            await refresh_account();
            navigate('/account');

        } catch (caught) {
            set_error(caught.message);
        }
    }

    async function sign_out() {
        await logout();
        interview.reset();
        set_auth({authenticated: false});
        set_account(null);
        navigate('/login');
    }

    function start_setup() {
        interview.reset();
        restored_ref.current = true;
        navigate('/interview');
    }

    async function open_interview(interview_id) {
        interview.reset();
        restored_ref.current = true;
        await interview.resume(interview_id, bootstrap.job.title);
        navigate('/interview');
    }

    function return_to_account() {
        interview.reset();
        restored_ref.current = false;
        refresh_account();
        navigate('/account');
    }

    if (!bootstrap || !auth) {
        return <main className="grid min-h-screen place-items-center text-slate-300">{error || 'Loading…'}</main>;
    }

    if (!auth.authenticated) {
        const mode = route === '/signup' ? 'signup' : 'login';
        return <AuthScreen mode={mode} error={error} on_submit={(email, password) => submit_auth(mode, email, password)} on_switch={() => navigate(mode === 'signup' ? '/login' : '/signup')} />;
    }

    if (route === '/interview') {
        if (interview.ended) {
            return <CompleteScreen interview={interview} on_account={return_to_account} />;
        }

        if (interview.session) {
            return <InterviewScreen interview={interview} on_account={return_to_account} />;
        }

        return <SetupScreen bootstrap={bootstrap} on_start={(payload) => interview.begin(payload).catch((caught) => set_error(caught.message))} on_account={return_to_account} error={error || interview.error} />;
    }

    if (!account) {
        return <main className="grid min-h-screen place-items-center text-slate-300">{error || 'Loading account…'}</main>;
    }

    return <AccountScreen account={account} on_start={start_setup} on_resume={open_interview} on_view={open_interview} on_logout={sign_out} />;
}

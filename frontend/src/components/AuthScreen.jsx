import { useState } from 'react';

export default function AuthScreen({mode, on_submit, on_switch, error}) {
    const [email, set_email] = useState('');
    const [password, set_password] = useState('');
    const [submitting, set_submitting] = useState(false);
    const signup = mode === 'signup';

    async function submit(event) {
        event.preventDefault();
        set_submitting(true);

        try {
            await on_submit(email, password);

        } finally {
            set_submitting(false);
        }
    }

    return (
        <main className="mx-auto flex min-h-screen max-w-md items-center px-4 py-10 text-white">
            <section className="w-full rounded-3xl border border-white/10 bg-slate-950/80 p-6 shadow-2xl sm:p-8">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-300">AI interview</p>
                <h1 className="mt-3 text-3xl font-semibold">{signup ? 'Create your account' : 'Sign in'}</h1>
                <p className="mt-3 leading-7 text-slate-400">{signup ? 'Create an account so your interview and assessment stay linked to you.' : 'Sign in to continue to your interviews.'}</p>
                <form onSubmit={submit} className="mt-6">
                    <label htmlFor="email" className="block text-sm font-medium">Email</label>
                    <input id="email" type="email" required autoComplete="email" value={email} onChange={(event) => set_email(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-slate-700 bg-slate-900 px-3" />
                    <label htmlFor="password" className="mt-4 block text-sm font-medium">Password</label>
                    <input id="password" type="password" required autoComplete={signup ? 'new-password' : 'current-password'} value={password} onChange={(event) => set_password(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-slate-700 bg-slate-900 px-3" />
                    {error && <div role="alert" className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">{error}</div>}
                    <button disabled={submitting} className="mt-6 min-h-12 w-full rounded-xl bg-blue-500 px-5 font-semibold hover:bg-blue-400 disabled:opacity-50">{submitting ? 'Please wait…' : signup ? 'Create account' : 'Sign in'}</button>
                </form>
                <button type="button" onClick={on_switch} className="mt-5 w-full text-sm text-blue-300 underline underline-offset-4">{signup ? 'Already have an account? Sign in' : 'Need an account? Sign up'}</button>
            </section>
        </main>
    );
}

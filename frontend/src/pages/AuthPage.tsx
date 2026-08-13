import { useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import LanguageSelector from '../components/LanguageSelector';
import { useAuth } from '../hooks/useAuth';

export default function AuthPage({mode}: {mode: 'login' | 'signup'}) {
    const {t} = useTranslation();
    const navigate = useNavigate();
    const {auth, sign_in, sign_up} = useAuth();
    const [email, set_email] = useState('');
    const [password, set_password] = useState('');
    const [submitting, set_submitting] = useState(false);
    const [error, set_error] = useState('');
    const signup = mode === 'signup';

    if (auth?.authenticated) {
        return <Navigate to="/jobs" replace />;
    }

    async function submit(event: FormEvent) {
        event.preventDefault();
        set_submitting(true);
        set_error('');

        try {
            if (signup) {
                await sign_up(email, password);
            } else {
                await sign_in(email, password);
            }

            navigate('/jobs', {replace: true});
        } catch (caught) {
            set_error(caught instanceof Error ? caught.message : t('errors.request'));
        } finally {
            set_submitting(false);
        }
    }

    return (
        <main className="auth-page">
            <div className="auth-language"><LanguageSelector /></div>
            <section className="auth-layout">
                <div className="auth-intro">
                    <span className="brand-mark large">AI</span>
                    <p className="eyebrow">{t('auth.brand')}</p>
                    <h1>{signup ? t('auth.signupTitle') : t('auth.loginTitle')}</h1>
                    <p>{signup ? t('auth.signupDescription') : t('auth.loginDescription')}</p>
                </div>
                <form onSubmit={submit} className="auth-card">
                    <label htmlFor="email">{t('auth.email')}</label>
                    <input id="email" type="email" required autoComplete="email" value={email} onChange={(event) => set_email(event.target.value)} />
                    <label htmlFor="password">{t('auth.password')}</label>
                    <input id="password" type="password" required autoComplete={signup ? 'new-password' : 'current-password'} value={password} onChange={(event) => set_password(event.target.value)} />
                    {error && <div role="alert" className="error-banner">{error}</div>}
                    <button disabled={submitting} className="primary-button auth-submit">{submitting ? t('auth.wait') : signup ? t('auth.createAccount') : t('auth.signIn')}</button>
                    <button type="button" onClick={() => navigate(signup ? '/login' : '/signup')} className="text-button">{signup ? t('auth.toLogin') : t('auth.toSignup')}</button>
                </form>
            </section>
        </main>
    );
}

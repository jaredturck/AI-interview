import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { get_application, get_bootstrap, start_application_interview } from '../api';
import LoadingScreen from '../components/LoadingScreen';
import type { BootstrapData, JobApplication } from '../types';

export default function InterviewSetupPage() {
    const {t} = useTranslation();
    const {application_id = ''} = useParams();
    const navigate = useNavigate();
    const [application, set_application] = useState<JobApplication | null>(null);
    const [bootstrap, set_bootstrap] = useState<BootstrapData | null>(null);
    const [confirm_transcript, set_confirm_transcript] = useState(false);
    const [mic_status, set_mic_status] = useState('notTested');
    const [starting, set_starting] = useState(false);
    const [error, set_error] = useState('');

    useEffect(() => {
        Promise.all([get_application(application_id), get_bootstrap()]).then(([application_data, bootstrap_data]) => {
            set_application(application_data.application);
            set_bootstrap(bootstrap_data);

            if (application_data.application.interview) {
                navigate(`/interviews/${application_data.application.interview.id}`, {replace: true});
            }
        }).catch((caught) => set_error(caught.message));
    }, [application_id, navigate]);

    function test_microphone() {
        if (!navigator.mediaDevices?.getUserMedia) {
            set_mic_status('unavailable');
            return;
        }

        set_mic_status('checking');
        navigator.mediaDevices.getUserMedia({audio: true}).then((stream) => {
            stream.getTracks().forEach((track) => track.stop());
            set_mic_status('ready');
        }).catch(() => set_mic_status('unavailable'));
    }

    async function submit(event: FormEvent) {
        event.preventDefault();
        set_starting(true);
        set_error('');

        try {
            const data = await start_application_interview(application_id, {confirm_transcript});
            navigate(`/interviews/${data.interview.id}`, {replace: true});
        } catch (caught) {
            set_error(caught instanceof Error ? caught.message : t('errors.request'));
        } finally {
            set_starting(false);
        }
    }

    if ((!application || !bootstrap) && !error) {
        return <LoadingScreen />;
    }

    return (
        <main className="setup-page">
            <section className="setup-layout">
                <div className="setup-intro">
                    <Link to={`/applications/${application_id}`} className="back-link">← {t('setup.back')}</Link>
                    <p className="eyebrow">{t('setup.eyebrow')}</p>
                    <h1>{t('setup.title')}</h1>
                    <p className="setup-lead">{t('setup.description')}</p>
                    <div className="setup-features">
                        <div>{t('setup.featureRephrase')}</div><div>{t('setup.featurePause')}</div><div>{t('setup.featureTranscript')}</div><div>{t('setup.featureReview')}</div>
                    </div>
                </div>
                <form onSubmit={submit} className="setup-card">
                    <div className="setup-job"><span>{application?.job.title}</span>{application?.job.subtitle && <small>{application.job.subtitle}</small>}</div>
                    <h2>{t('setup.panelTitle')}</h2>
                    <p>{t('setup.duration', {minutes: bootstrap?.max_minutes})}</p>
                    <p>{t('setup.privacy')}</p>
                    {bootstrap && <p>{t('setup.contact', {email: bootstrap.recruitment_email})}</p>}
                    <label className="check-card">
                        <input type="checkbox" checked={confirm_transcript} onChange={(event) => set_confirm_transcript(event.target.checked)} />
                        <span><strong>{t('setup.confirmTitle')}</strong><small>{t('setup.confirmDescription')}</small></span>
                    </label>
                    <div className="microphone-card">
                        <div><strong>{t('setup.microphone')}</strong><span>{t(`setup.${mic_status}`)}</span></div>
                        <button type="button" onClick={test_microphone} className="secondary-button">{t('setup.test')}</button>
                    </div>
                    {error && <div role="alert" className="error-banner">{error}</div>}
                    <button disabled={starting || !application || !bootstrap} className="primary-button setup-start">{starting ? t('setup.starting') : t('setup.start')}</button>
                </form>
            </section>
        </main>
    );
}

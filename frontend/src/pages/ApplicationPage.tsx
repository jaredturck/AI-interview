import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { get_application } from '../api';
import LoadingScreen from '../components/LoadingScreen';
import StatusBadge from '../components/StatusBadge';
import type { JobApplication } from '../types';

export default function ApplicationPage() {
    const {t} = useTranslation();
    const {application_id = ''} = useParams();
    const [application, set_application] = useState<JobApplication | null>(null);
    const [error, set_error] = useState('');

    useEffect(() => {
        get_application(application_id).then((data) => set_application(data.application)).catch((caught) => set_error(caught.message));
    }, [application_id]);

    if (!application && !error) {
        return <LoadingScreen />;
    }

    const interview = application?.interview;
    let action = application ? <Link to={`/applications/${application.id}/interview`} className="primary-button">{t('application.start')}</Link> : null;

    if (interview && ['created', 'active'].includes(interview.status)) {
        action = <Link to={`/interviews/${interview.id}`} className="primary-button">{t('application.resume')}</Link>;
    } else if (interview) {
        action = <Link to={`/interviews/${interview.id}`} className="primary-button">{t('application.viewResult')}</Link>;
    }

    return (
        <main className="page-shell narrow-page">
            <Link to="/account" className="back-link">← {t('application.back')}</Link>
            {error && <div role="alert" className="error-banner">{error}</div>}
            {application && <>
                <section className="application-hero">
                    <div><p className="eyebrow">{t('application.eyebrow')}</p><h1>{application.job.title}</h1>{application.job.subtitle && <p className="detail-subtitle">{application.job.subtitle}</p>}</div>
                    <StatusBadge application_status={application.status} result={interview?.result || ''} />
                </section>
                <section className="application-panel">
                    <div className="application-panel-row"><span>{t('application.status')}</span><strong>{t(`applicationStatus.${application.status}`)}</strong></div>
                    <div className="application-panel-row"><span>{t('application.interview')}</span><strong>{interview ? t(`interviewStatus.${interview.status}`) : t('applicationStatus.interview_pending')}</strong></div>
                    <div className="application-action-card">
                        {!interview && <><h2>{t('application.pendingTitle')}</h2><p>{t('application.pendingDescription')}</p></>}
                        {interview && ['completed', 'terminated', 'evaluating'].includes(interview.status) && <><h2>{t('application.evaluatingTitle')}</h2><p>{t('application.evaluatingDescription')}</p></>}
                        {action}
                    </div>
                </section>
                <section className="detail-card compact-detail"><p className="eyebrow">{t('jobs.descriptionLabel')}</p><div className="job-description">{application.job.description}</div></section>
            </>}
        </main>
    );
}

import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { apply_job, get_job } from '../api';
import LoadingScreen from '../components/LoadingScreen';
import StatusBadge from '../components/StatusBadge';
import type { JobSummary } from '../types';

export default function JobDetailPage() {
    const {t} = useTranslation();
    const {job_id = ''} = useParams();
    const navigate = useNavigate();
    const [job, set_job] = useState<JobSummary | null>(null);
    const [applying, set_applying] = useState(false);
    const [error, set_error] = useState('');

    useEffect(() => {
        get_job(job_id).then((data) => set_job(data.job)).catch((caught) => set_error(caught.message));
    }, [job_id]);

    async function apply() {
        set_applying(true);
        set_error('');

        try {
            const data = await apply_job(job_id);
            navigate(`/applications/${data.application.id}`);
        } catch (caught) {
            set_error(caught instanceof Error ? caught.message : t('errors.request'));
        } finally {
            set_applying(false);
        }
    }

    if (!job && !error) {
        return <LoadingScreen />;
    }

    return (
        <main className="page-shell narrow-page">
            <Link to="/jobs" className="back-link">← {t('job.back')}</Link>
            {error && <div role="alert" className="error-banner">{error}</div>}
            {job && <article className="detail-card">
                <div className="detail-heading">
                    <div><p className="eyebrow">{t('jobs.descriptionLabel')}</p><h1>{job.title}</h1>{job.subtitle && <p className="detail-subtitle">{job.subtitle}</p>}</div>
                    {job.application && <StatusBadge application_status={job.application.status} />}
                </div>
                <div className="job-description">{job.description}</div>
                <div className="detail-actions">
                    {job.application ? <Link to={`/applications/${job.application.id}`} className="primary-button">{t('job.viewApplication')}</Link> :
                        <button type="button" onClick={apply} disabled={applying} className="primary-button">{applying ? t('job.applying') : t('job.apply')}</button>}
                </div>
            </article>}
        </main>
    );
}

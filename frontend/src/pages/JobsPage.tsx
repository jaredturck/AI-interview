import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { get_jobs } from '../api';
import LoadingScreen from '../components/LoadingScreen';
import StatusBadge from '../components/StatusBadge';
import type { JobSummary } from '../types';

export default function JobsPage() {
    const {t} = useTranslation();
    const [jobs, set_jobs] = useState<JobSummary[] | null>(null);
    const [error, set_error] = useState('');

    useEffect(() => {
        get_jobs().then((data) => set_jobs(data.jobs)).catch((caught) => set_error(caught.message));
    }, []);

    if (!jobs && !error) {
        return <LoadingScreen />;
    }

    return (
        <main className="page-shell">
            <section className="page-heading">
                <p className="eyebrow">{t('jobs.eyebrow')}</p>
                <h1>{t('jobs.title')}</h1>
                <p>{t('jobs.description')}</p>
            </section>
            {error && <div role="alert" className="error-banner">{error}</div>}
            <section className="jobs-grid">
                {jobs?.length === 0 && <div className="empty-card">{t('jobs.empty')}</div>}
                {jobs?.map((job) => (
                    <article key={job.id} className="job-card">
                        <div className="job-card-top">
                            <div><h2>{job.title}</h2>{job.subtitle && <p className="job-subtitle">{job.subtitle}</p>}</div>
                            {job.application && <StatusBadge application_status={job.application.status} />}
                        </div>
                        <p className="job-excerpt">{job.description_excerpt}</p>
                        <div className="job-card-actions">
                            <Link to={`/jobs/${job.id}`} className="secondary-button">{t('jobs.viewRole')}</Link>
                            {job.application && <Link to={`/applications/${job.application.id}`} className="text-link">{t('job.viewApplication')} →</Link>}
                        </div>
                    </article>
                ))}
            </section>
        </main>
    );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { get_account } from '../api';
import LoadingScreen from '../components/LoadingScreen';
import StatusBadge from '../components/StatusBadge';
import type { AccountData } from '../types';

export default function AccountPage() {
    const {t, i18n} = useTranslation();
    const [account, set_account] = useState<AccountData | null>(null);
    const [error, set_error] = useState('');

    useEffect(() => {
        get_account().then(set_account).catch((caught) => set_error(caught.message));
    }, []);

    if (!account && !error) {
        return <LoadingScreen />;
    }

    function format_date(value: string) {
        return new Intl.DateTimeFormat(i18n.resolvedLanguage || i18n.language, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value));
    }

    return (
        <main className="page-shell">
            <section className="page-heading account-heading">
                <p className="eyebrow">{t('account.eyebrow')}</p>
                <h1>{t('account.title')}</h1>
                <p>{account ? t('account.signedIn', {email: account.email}) : ''}</p>
                <p>{t('account.description')}</p>
            </section>
            {error && <div role="alert" className="error-banner">{error}</div>}
            <section className="applications-list">
                {account?.applications.length === 0 && <div className="empty-card">{t('account.empty')}</div>}
                {account?.applications.map((application) => (
                    <article key={application.id} className="application-card">
                        <div className="application-card-main">
                            <div>
                                <h2>{application.job.title}</h2>
                                {application.job.subtitle && <p className="job-subtitle">{application.job.subtitle}</p>}
                                <p className="application-date">{t('account.applied', {date: format_date(application.applied_at)})}</p>
                            </div>
                            <StatusBadge application_status={application.status} result={application.interview?.result || ''} />
                        </div>
                        <Link to={`/applications/${application.id}`} className="secondary-button">{t('common.view')}</Link>
                    </article>
                ))}
            </section>
        </main>
    );
}

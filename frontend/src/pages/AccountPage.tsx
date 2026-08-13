import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { delete_all_interview_data, delete_interview_data, get_account } from '../api';
import LoadingScreen from '../components/LoadingScreen';
import StatusBadge from '../components/StatusBadge';
import type { AccountData, JobApplication } from '../types';

export default function AccountPage() {
    const {t, i18n} = useTranslation();
    const [account, set_account] = useState<AccountData | null>(null);
    const [error, set_error] = useState('');
    const [menu_id, set_menu_id] = useState('');
    const [delete_application, set_delete_application] = useState<JobApplication | null>(null);
    const [delete_all_open, set_delete_all_open] = useState(false);
    const [deleting, set_deleting] = useState(false);

    useEffect(() => {
        get_account().then(set_account).catch((caught) => set_error(caught.message));
    }, []);

    if (!account && !error) {
        return <LoadingScreen />;
    }

    function format_date(value: string) {
        return new Intl.DateTimeFormat(i18n.resolvedLanguage || i18n.language, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value));
    }

    async function delete_selected_interview() {
        if (!delete_application?.interview || !account) {
            return;
        }

        set_deleting(true);
        set_error('');

        try {
            await delete_interview_data(delete_application.interview.id);
            set_account({...account, applications: account.applications.map((application) => application.id === delete_application.id ?
                {...application, status: 'withdrawn', interview: null} : application)});
            set_delete_application(null);
            set_menu_id('');
        } catch (caught) {
            set_error(caught instanceof Error ? caught.message : t('errors.request'));
        } finally {
            set_deleting(false);
        }
    }

    async function delete_all_data() {
        if (!account) {
            return;
        }

        set_deleting(true);
        set_error('');

        try {
            await delete_all_interview_data();
            set_account({...account, applications: []});
            set_delete_all_open(false);
            set_menu_id('');
        } catch (caught) {
            set_error(caught instanceof Error ? caught.message : t('errors.request'));
        } finally {
            set_deleting(false);
        }
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
                        <div className="application-card-actions">
                            <Link to={`/applications/${application.id}`} className="secondary-button">{t('common.view')}</Link>
                            {application.interview && <div className="application-menu-wrap">
                                <button type="button" className="application-menu-button" aria-label={t('account.moreActions')}
                                    aria-expanded={menu_id === application.id} onClick={() => set_menu_id(menu_id === application.id ? '' : application.id)}>⋯</button>
                                {menu_id === application.id && <div className="application-menu" role="menu">
                                    <button type="button" role="menuitem" onClick={() => {
                                        set_menu_id('');
                                        set_delete_application(application);
                                    }}>
                                        <span aria-hidden="true">🗑</span>{t('account.deleteInterview')}
                                    </button>
                                </div>}
                            </div>}
                        </div>
                    </article>
                ))}
            </section>
            {account && <section className="privacy-card">
                <div>
                    <p className="eyebrow">{t('account.privacyEyebrow')}</p>
                    <h2>{t('account.privacyTitle')}</h2>
                    <p>{t('account.privacyDescription')}</p>
                </div>
                <div className="privacy-actions">
                    <a href="/api/account/transcripts/" download className="secondary-button">{t('account.downloadTranscripts')}</a>
                    <button type="button" className="danger-button" onClick={() => set_delete_all_open(true)}>{t('account.deleteAllData')}</button>
                </div>
            </section>}
            {delete_application && <div className="confirm-backdrop">
                <section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-interview-title">
                    <p className="eyebrow">{t('account.deleteInterviewEyebrow')}</p>
                    <h2 id="delete-interview-title">{t('account.deleteInterviewTitle')}</h2>
                    <p>{t('account.deleteInterviewWarning', {job: delete_application.job.title})}</p>
                    <div className="confirm-actions">
                        <button type="button" className="secondary-button" disabled={deleting} onClick={() => set_delete_application(null)}>{t('common.cancel')}</button>
                        <button type="button" className="danger-button" disabled={deleting} onClick={delete_selected_interview}>
                            {deleting ? t('account.deleting') : t('account.deleteInterview')}
                        </button>
                    </div>
                </section>
            </div>}
            {delete_all_open && <div className="confirm-backdrop">
                <section className="confirm-dialog destructive-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-all-title">
                    <p className="destructive-label">{t('account.deleteAllHeading')}</p>
                    <h2 id="delete-all-title">{t('account.deleteAllTitle')}</h2>
                    <p>{t('account.deleteAllWarning')}</p>
                    <div className="confirm-actions">
                        <button type="button" className="secondary-button" disabled={deleting} onClick={() => set_delete_all_open(false)}>{t('common.cancel')}</button>
                        <button type="button" className="danger-button" disabled={deleting} onClick={delete_all_data}>
                            {deleting ? t('account.deleting') : t('common.continue')}
                        </button>
                    </div>
                </section>
            </div>}
        </main>
    );
}

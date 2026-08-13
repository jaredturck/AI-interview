import { useState } from 'react';
import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { submit_review } from '../api';

export default function ReviewForm({interview_id, already_submitted}: {interview_id: string; already_submitted: boolean}) {
    const {t} = useTranslation();
    const [open, set_open] = useState(false);
    const [explanation, set_explanation] = useState('');
    const [submitted, set_submitted] = useState(already_submitted);
    const [error, set_error] = useState('');

    async function submit(event: FormEvent) {
        event.preventDefault();
        set_error('');

        try {
            await submit_review(interview_id, explanation);
            set_submitted(true);
        } catch (caught) {
            set_error(caught instanceof Error ? caught.message : t('errors.request'));
        }
    }

    if (submitted) {
        return <div className="review-submitted">{t('review.submitted')}</div>;
    }

    if (!open) {
        return <button type="button" onClick={() => set_open(true)} className="secondary-button mt-6">{t('review.request')}</button>;
    }

    return (
        <form onSubmit={submit} className="review-form">
            <h2>{t('review.title')}</h2>
            <p>{t('review.description')}</p>
            <label htmlFor="review-explanation">{t('review.label')}</label>
            <textarea id="review-explanation" required value={explanation} onChange={(event) => set_explanation(event.target.value)} rows={5} />
            {error && <div role="alert" className="error-banner">{error}</div>}
            <button className="primary-button">{t('review.submit')}</button>
        </form>
    );
}

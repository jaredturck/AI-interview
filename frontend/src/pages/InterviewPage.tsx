import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import interviewer_image from '../assets/interviewer.png';
import InterviewControls from '../components/InterviewControls';
import LanguageSelector from '../components/LanguageSelector';
import LoadingScreen from '../components/LoadingScreen';
import ReviewForm from '../components/ReviewForm';
import StatusBadge from '../components/StatusBadge';
import Transcript from '../components/Transcript';
import TranscriptConfirmation from '../components/TranscriptConfirmation';
import useInterview from '../hooks/useInterview';

export default function InterviewPage() {
    const {t} = useTranslation();
    const {interview_id = ''} = useParams();
    const [transcript_open, set_transcript_open] = useState(false);
    const interview = useInterview(interview_id);

    if (!interview.loaded) {
        return <LoadingScreen />;
    }

    if (interview.ended) {
        const evaluated = Boolean(interview.result);
        const progressed = interview.result === 'PROGRESS';
        const evaluation_failed = interview.status === 'evaluation_failed';

        return (
            <main className="complete-page">
                <div className="complete-language"><LanguageSelector /></div>
                <section className="complete-card">
                    <div className="complete-mark" aria-hidden="true">✓</div>
                    <p className="eyebrow">{interview.job?.title}</p>
                    <h1>{t('complete.title')}</h1>
                    <div role="status" aria-live="polite" className="complete-copy">
                        {!evaluated && !evaluation_failed && <p>{t('complete.processing')}</p>}
                        {evaluation_failed && <p>{t('complete.failed')}</p>}
                        {evaluated && progressed && <p>{t('complete.progress')}</p>}
                        {evaluated && !progressed && <p>{t('complete.noProgress')}</p>}
                    </div>
                    {(evaluated || evaluation_failed) && <ReviewForm interview_id={interview_id} already_submitted={interview.review_requested} />}
                    <Link to="/account" className="secondary-button mt-6">{t('complete.returnAccount')}</Link>
                </section>
            </main>
        );
    }

    return (
        <main className="interview-shell">
            <div className="sr-only" aria-live="polite" aria-atomic="true">{interview.latest_assistant}</div>
            <header className="interview-header">
                <div className="interview-identity">
                    <span className="brand-mark">AI</span>
                    <div><strong>{t('interview.interviewer')}</strong><span>{interview.job?.title}{interview.job?.subtitle ? ` · ${interview.job.subtitle}` : ''}</span></div>
                </div>
                <div className="interview-header-actions">
                    <StatusBadge live_status={interview.status} />
                    <button type="button" className="mobile-transcript-button" onClick={() => set_transcript_open(!transcript_open)}>
                        {transcript_open ? t('interview.closeTranscript') : t('interview.openTranscript')}
                    </button>
                    <LanguageSelector compact />
                    <Link to="/account" className="ghost-button">{t('interview.account')}</Link>
                </div>
            </header>
            {interview.error && interview.microphone_setup_complete && <div role="alert" className="interview-error">{interview.error}</div>}
            {!interview.microphone_setup_complete && <div className="microphone-consent-backdrop">
                <section className="microphone-consent" role="dialog" aria-modal="true" aria-labelledby="microphone-consent-title">
                    <div className="microphone-consent-icon" aria-hidden="true">●</div>
                    <p className="eyebrow">{t('interview.microphoneSetup')}</p>
                    <h2 id="microphone-consent-title">{t('interview.microphoneTitle')}</h2>
                    <p>{t('interview.microphoneDescription')}</p>
                    {interview.error && <div role="alert" className="error-banner">{interview.error}</div>}
                    <div className="microphone-consent-actions">
                        <button type="button" disabled={interview.microphone_requesting} onClick={interview.enable_open_microphone} className="primary-button">
                            {interview.microphone_requesting ? t('interview.enablingMic') : t('interview.enableOpenMic')}
                        </button>
                        <button type="button" disabled={interview.microphone_requesting} onClick={interview.use_closed_microphone} className="secondary-button">
                            {t('interview.usePushToTalk')}
                        </button>
                    </div>
                    <small>{t('interview.microphonePrivacy')}</small>
                </section>
            </div>}
            <div className="interview-workspace">
                <section className="call-stage" aria-label={t('interview.interviewer')}>
                    <img src={interviewer_image} alt={t('interview.interviewer')} className="interviewer-image" />
                    <div className="call-stage-gradient" />
                    <div className="participant-label"><span className="participant-dot" />{t('interview.interviewer')}</div>
                    <div className="job-overlay"><strong>{interview.job?.title}</strong>{interview.job?.subtitle && <span>{interview.job.subtitle}</span>}</div>
                    <div className="stage-controls">
                        <TranscriptConfirmation text={interview.pending_transcript} on_confirm={interview.confirm_transcript} />
                        <InterviewControls interview={interview} />
                    </div>
                </section>
                <aside className={`transcript-panel ${transcript_open ? 'open' : ''}`}>
                    <div className="transcript-header">
                        <div><p className="eyebrow">{t('application.interview')}</p><h2>{t('interview.transcript')}</h2></div>
                        <button type="button" className="transcript-close" onClick={() => set_transcript_open(false)} aria-label={t('interview.closeTranscript')}>×</button>
                    </div>
                    <Transcript messages={interview.messages} candidate_pending={interview.candidate_pending} assistant_pending={interview.assistant_pending} />
                </aside>
            </div>
        </main>
    );
}

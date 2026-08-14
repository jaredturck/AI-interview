import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';

import type { TranscriptMessage, TranscriptRole } from '../types';

interface TranscriptProps {
    messages: TranscriptMessage[];
    candidate_pending: boolean;
    assistant_pending: boolean;
}

function PendingMessage({role}: {role: TranscriptRole}) {
    const {t} = useTranslation();
    const label = role === 'user' ? t('common.pending') : t('liveStatus.thinking');

    return (
        <article className={`transcript-message ${role === 'user' ? 'candidate' : 'assistant'} pending`} aria-label={label}>
            <div className="transcript-speaker">{role === 'user' ? t('interview.you') : t('interview.interviewer')}</div>
            <p className="typing-indicator" aria-hidden="true"><span /><span /><span /></p>
        </article>
    );
}

export default function Transcript({messages, candidate_pending, assistant_pending}: TranscriptProps) {
    const {t} = useTranslation();
    const end_ref = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        end_ref.current?.scrollIntoView({behavior: 'auto', block: 'end'});
    }, [messages, candidate_pending, assistant_pending]);

    const empty = messages.length === 0 && !candidate_pending && !assistant_pending;

    return (
        <div className="transcript-scroll" aria-label={t('interview.transcript')}>
            {empty && <p className="transcript-empty">{t('interview.transcriptEmpty')}</p>}
            <div className="transcript-messages">
                {messages.map((message) => (
                    <article key={message.id} className={`transcript-message ${message.role === 'user' ? 'candidate' : 'assistant'}`}>
                        <div className="transcript-speaker">{message.role === 'user' ? t('interview.you') : t('interview.interviewer')}</div>
                        <p>{message.text}</p>
                    </article>
                ))}
                {candidate_pending && <PendingMessage role="user" />}
                {assistant_pending && <PendingMessage role="assistant" />}
                <div ref={end_ref} />
            </div>
        </div>
    );
}

import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';

import type { TranscriptMessage } from '../types';

export default function Transcript({messages}: {messages: TranscriptMessage[]}) {
    const {t} = useTranslation();
    const end_ref = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        end_ref.current?.scrollIntoView({behavior: 'auto', block: 'end'});
    }, [messages]);

    return (
        <div className="transcript-scroll" aria-label={t('interview.transcript')}>
            {messages.length === 0 && <p className="transcript-empty">{t('interview.transcriptEmpty')}</p>}
            <div className="transcript-messages">
                {messages.map((message) => (
                    <article key={message.id} className={`transcript-message ${message.role === 'user' ? 'candidate' : 'assistant'}`}>
                        <div className="transcript-speaker">{message.role === 'user' ? t('interview.you') : t('interview.interviewer')}</div>
                        <p>{message.text}</p>
                    </article>
                ))}
                <div ref={end_ref} />
            </div>
        </div>
    );
}

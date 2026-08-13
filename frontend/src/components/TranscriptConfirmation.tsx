import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

export default function TranscriptConfirmation({text, on_confirm}: {text: string; on_confirm: (text: string) => void}) {
    const {t} = useTranslation();
    const [value, set_value] = useState(text);

    useEffect(() => set_value(text), [text]);

    if (!text) {
        return null;
    }

    return (
        <section className="transcript-confirmation" aria-labelledby="transcript-confirmation-title">
            <div>
                <h2 id="transcript-confirmation-title">{t('interview.checkTranscript')}</h2>
                <p>{t('interview.checkTranscriptDescription')}</p>
            </div>
            <textarea aria-label={t('interview.correctedTranscript')} value={value} onChange={(event) => set_value(event.target.value)} rows={2} />
            <button type="button" onClick={() => on_confirm(value)}>{t('interview.useTranscript')}</button>
        </section>
    );
}

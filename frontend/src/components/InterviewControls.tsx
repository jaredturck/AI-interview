import { useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { useTranslation } from 'react-i18next';

import type useInterview from '../hooks/useInterview';

type InterviewController = ReturnType<typeof useInterview>;

export default function InterviewControls({interview}: {interview: InterviewController}) {
    const {t} = useTranslation();
    const [text, set_text] = useState('');
    const textarea_ref = useRef<HTMLTextAreaElement | null>(null);
    const response_busy = ['idle', 'thinking', 'transcribing', 'speaking', 'connecting', 'loading'].includes(interview.status);
    const voice_busy = response_busy || interview.status === 'confirming';

    function resize_input(value: string) {
        set_text(value);

        if (textarea_ref.current) {
            textarea_ref.current.style.height = '38px';
            textarea_ref.current.style.height = `${Math.min(textarea_ref.current.scrollHeight, 112)}px`;
        }
    }

    function submit(event: FormEvent) {
        event.preventDefault();
        if (interview.send_text(text)) {
            resize_input('');
        }
    }

    function handle_key_down(event: KeyboardEvent<HTMLTextAreaElement>) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            event.currentTarget.form?.requestSubmit();
        }
    }

    return (
        <div className="control-island">
            <form onSubmit={submit} className="response-row">
                <label htmlFor="typed-response" className="sr-only">{t('interview.typeResponse')}</label>
                <textarea ref={textarea_ref} id="typed-response" value={text} onChange={(event) => resize_input(event.target.value)} onKeyDown={handle_key_down}
                    placeholder={t('interview.typeResponse')} rows={1} />
                <button type="submit" disabled={!text.trim() || response_busy} className="send-button">{t('interview.send')}</button>
            </form>
            <div className="control-row">
                <button type="button" disabled={voice_busy && !interview.is_recording} onClick={interview.is_recording ? interview.stop_recording : interview.start_recording}
                    className={interview.is_recording ? 'control-button recording' : 'control-button'}>
                    {interview.is_recording ? t('interview.finishSpeaking') : t('interview.speak')}
                </button>
                <button type="button" onClick={interview.replay} className="control-button">{t('interview.replay')}</button>
                <button type="button" disabled={voice_busy} onClick={interview.rephrase} className="control-button">{t('interview.rephrase')}</button>
                <button type="button" onClick={interview.need_moment} className="control-button">{t('interview.moment')}</button>
                <button type="button" onClick={() => interview.set_voice_enabled(!interview.voice_enabled)} className="control-button">
                    {interview.voice_enabled ? t('interview.muteVoice') : t('interview.enableVoice')}
                </button>
                <label className="speed-control">
                    <span>{t('interview.voiceSpeed')}</span>
                    <select value={interview.speech_speed} onChange={(event) => interview.set_speech_speed(Number(event.target.value))}>
                        <option value="0.75">0.75×</option><option value="1">1×</option><option value="1.25">1.25×</option><option value="1.5">1.5×</option>
                    </select>
                </label>
                <button type="button" onClick={interview.end_interview} className="control-button end-control">{t('interview.end')}</button>
            </div>
        </div>
    );
}

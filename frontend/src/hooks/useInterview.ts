import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { get_interview_status } from '../api';
import type { InterviewResult, InterviewStatusResponse, JobSummary, LiveStatus, TranscriptMessage, TranscriptRole, WebSocketMessage } from '../types';

const TERMINAL_STATUSES = ['completed', 'terminated', 'evaluating', 'evaluated', 'evaluation_failed'];

export default function useInterview(interview_id: string) {
    const {t} = useTranslation();
    const [job, set_job] = useState<JobSummary | null>(null);
    const [application_id, set_application_id] = useState('');
    const [messages, set_messages] = useState<TranscriptMessage[]>([]);
    const [status, set_status] = useState<LiveStatus>('idle');
    const [error, set_error] = useState('');
    const [pending_transcript, set_pending_transcript] = useState('');
    const [ended, set_ended] = useState(false);
    const [result, set_result] = useState<InterviewResult>('');
    const [review_requested, set_review_requested] = useState(false);
    const [speech_speed, set_speech_speed] = useState(1);
    const [voice_enabled, set_voice_enabled] = useState(true);
    const [is_recording, set_is_recording] = useState(false);
    const [latest_assistant, set_latest_assistant] = useState('');
    const [loaded, set_loaded] = useState(false);
    const websocket_ref = useRef<WebSocket | null>(null);
    const recorder_ref = useRef<MediaRecorder | null>(null);
    const stream_ref = useRef<MediaStream | null>(null);
    const last_audio_ref = useRef<HTMLAudioElement | null>(null);
    const speech_speed_ref = useRef(1);
    const voice_enabled_ref = useRef(true);
    const audio_playing_ref = useRef(false);

    useEffect(() => {
        load_interview();
        return cleanup_resources;
    }, [interview_id]);

    useEffect(() => {
        speech_speed_ref.current = speech_speed;

        if (last_audio_ref.current) {
            last_audio_ref.current.playbackRate = speech_speed;
        }
    }, [speech_speed]);

    useEffect(() => {
        voice_enabled_ref.current = voice_enabled;

        if (!voice_enabled && last_audio_ref.current && audio_playing_ref.current) {
            last_audio_ref.current.pause();
            audio_playing_ref.current = false;
            set_status('ready');
        }
    }, [voice_enabled]);

    useEffect(() => {
        if (!ended || result || status === 'evaluation_failed') {
            return;
        }

        const poll = window.setInterval(refresh_status, 3000);
        return () => window.clearInterval(poll);
    }, [ended, result, status, interview_id]);

    async function load_interview() {
        set_error('');

        try {
            const current = await get_interview_status(interview_id);
            apply_status(current);
            set_loaded(true);

            if (!TERMINAL_STATUSES.includes(current.interview.status)) {
                connect_session();
            }
        } catch (caught) {
            set_error(caught instanceof Error ? caught.message : t('errors.request'));
            set_loaded(true);
        }
    }

    async function refresh_status() {
        try {
            apply_status(await get_interview_status(interview_id));
        } catch {
            return;
        }
    }

    function apply_status(current: InterviewStatusResponse) {
        set_job(current.job);
        set_application_id(current.application.id);
        set_result(current.interview.result || '');
        set_review_requested(Boolean(current.interview.review_requested));

        if (TERMINAL_STATUSES.includes(current.interview.status)) {
            set_ended(true);
            set_status(current.interview.status === 'evaluation_failed' ? 'evaluation_failed' : 'complete');
        }
    }

    function append_message(role: TranscriptRole, text: string) {
        set_messages((current) => [...current, {role, text, id: crypto.randomUUID()}]);

        if (role === 'assistant') {
            set_latest_assistant(text);
        }
    }

    function play_audio(buffer: ArrayBuffer) {
        const blob = new Blob([buffer], {type: 'audio/wav'});
        const url = URL.createObjectURL(blob);

        if (last_audio_ref.current) {
            last_audio_ref.current.pause();
            URL.revokeObjectURL(last_audio_ref.current.src);
        }

        const audio = new Audio(url);
        audio.playbackRate = speech_speed_ref.current;
        audio.onended = () => {
            audio_playing_ref.current = false;
            set_status('ready');
        };
        last_audio_ref.current = audio;

        if (!voice_enabled_ref.current) {
            return;
        }

        audio_playing_ref.current = true;
        set_status('speaking');
        audio.play().catch(() => {
            audio_playing_ref.current = false;
            set_status('ready');
            set_error(t('errors.audioBlocked'));
        });
    }

    function handle_socket_message(event: MessageEvent) {
        if (event.data instanceof ArrayBuffer) {
            play_audio(event.data);
            return;
        }

        const message = JSON.parse(event.data as string) as WebSocketMessage;

        if (message.type === 'history') {
            set_messages(message.turns.map((turn) => ({...turn, id: crypto.randomUUID()})));
            const last_assistant = [...message.turns].reverse().find((turn) => turn.role === 'assistant');

            if (last_assistant) {
                set_latest_assistant(last_assistant.text);
            }
        } else if (message.type === 'ready') {
            if (!audio_playing_ref.current) {
                set_status('ready');
            }
        } else if (message.type === 'status') {
            if (message.status !== 'ready' || !audio_playing_ref.current) {
                set_status(message.status);
            }
        } else if (message.type === 'candidate') {
            append_message('user', message.text);
        } else if (message.type === 'assistant') {
            append_message('assistant', message.text);
        } else if (message.type === 'transcription' && message.requires_confirmation) {
            set_pending_transcript(message.text);
        } else if (message.type === 'ended') {
            set_ended(true);
            set_result(message.result || '');
            set_status(message.status === 'evaluation_failed' ? 'evaluation_failed' : 'complete');
        } else if (message.type === 'audio_unavailable') {
            set_error(t('errors.audioUnavailable'));
        } else if (message.type === 'error') {
            set_error(message.code ? t(`errors.${message.code}`, {defaultValue: message.message}) : message.message);
            set_status('ready');
        }
    }

    function connect_session() {
        set_status('connecting');
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const socket = new WebSocket(`${protocol}://${window.location.host}/ws/interviews/${interview_id}/`);
        socket.binaryType = 'arraybuffer';
        socket.onmessage = handle_socket_message;
        socket.onerror = () => set_error(t('errors.connection'));
        socket.onclose = (event) => {
            if (event.code === 4429) {
                set_error(t('errors.workerBusy'));
                set_status('idle');
            } else if ([4401, 4404, 4500].includes(event.code) && !ended) {
                set_status('idle');
            }
        };
        websocket_ref.current = socket;
    }

    function send_text(text: string) {
        const value = text.trim();

        if (!value || !websocket_ref.current || websocket_ref.current.readyState !== WebSocket.OPEN) {
            return false;
        }

        set_pending_transcript('');
        websocket_ref.current.send(JSON.stringify({type: 'text', text: value}));
        set_status('thinking');
        return true;
    }

    function start_recording() {
        set_error('');

        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
            set_error(t('errors.microphone'));
            return;
        }

        navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}}).then((stream) => {
            stream_ref.current = stream;
            const supported_types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
            const mime_type = supported_types.find((item) => MediaRecorder.isTypeSupported(item)) || '';
            const recorder = mime_type ? new MediaRecorder(stream, {mimeType: mime_type}) : new MediaRecorder(stream);
            const chunks: Blob[] = [];
            recorder_ref.current = recorder;
            recorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    chunks.push(event.data);
                }
            };
            recorder.onstop = async () => {
                const blob = new Blob(chunks, {type: recorder.mimeType || mime_type});
                const buffer = await blob.arrayBuffer();

                if (websocket_ref.current?.readyState === WebSocket.OPEN) {
                    websocket_ref.current.send(buffer);
                }

                stream.getTracks().forEach((track) => track.stop());
                stream_ref.current = null;
            };
            recorder.start();
            set_is_recording(true);
            set_status('listening');
        }).catch(() => set_error(t('errors.microphoneDenied')));
    }

    function stop_recording() {
        if (recorder_ref.current?.state === 'recording') {
            recorder_ref.current.stop();
        }

        set_is_recording(false);
    }

    function confirm_transcript(text: string) {
        websocket_ref.current?.send(JSON.stringify({type: 'confirm_transcript', text}));
        set_pending_transcript('');
    }

    function rephrase() {
        websocket_ref.current?.send(JSON.stringify({type: 'control', action: 'rephrase'}));
    }

    function need_moment() {
        if (last_audio_ref.current) {
            last_audio_ref.current.pause();
            audio_playing_ref.current = false;
        }

        websocket_ref.current?.send(JSON.stringify({type: 'control', action: 'moment'}));
        set_status('paused');
    }

    function end_interview() {
        websocket_ref.current?.send(JSON.stringify({type: 'control', action: 'end'}));
    }

    function replay() {
        if (!last_audio_ref.current) {
            return;
        }

        last_audio_ref.current.currentTime = 0;
        last_audio_ref.current.playbackRate = speech_speed_ref.current;
        audio_playing_ref.current = true;
        set_status('speaking');
        last_audio_ref.current.play().catch(() => {
            audio_playing_ref.current = false;
            set_status('ready');
        });
    }

    function cleanup_resources() {
        if (recorder_ref.current?.state === 'recording') {
            recorder_ref.current.stop();
        }

        stream_ref.current?.getTracks().forEach((track) => track.stop());
        stream_ref.current = null;
        recorder_ref.current = null;

        if (last_audio_ref.current) {
            last_audio_ref.current.pause();
            URL.revokeObjectURL(last_audio_ref.current.src);
            last_audio_ref.current = null;
        }

        audio_playing_ref.current = false;
        websocket_ref.current?.close();
        websocket_ref.current = null;
    }

    return {
        interview_id, job, application_id, messages, status, error, pending_transcript, ended, result, review_requested, speech_speed,
        set_speech_speed, voice_enabled, set_voice_enabled, is_recording, latest_assistant, loaded, send_text, start_recording,
        stop_recording, confirm_transcript, rephrase, need_moment, end_interview, replay, refresh_status,
    };
}

import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { get_interview_status } from '../api';
import type { InterviewResult, InterviewStatusResponse, JobSummary, LiveStatus, TranscriptMessage, TranscriptRole, WebSocketMessage } from '../types';

const TERMINAL_STATUSES = ['completed', 'terminated', 'evaluating', 'evaluated', 'evaluation_failed'];
const SILENCE_MS = 2000;
const SPEECH_THRESHOLD = 0.012;

type MicrophoneMode = 'open' | 'closed';

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
    const [microphone_mode, set_microphone_mode] = useState<MicrophoneMode>('open');
    const [microphone_active, set_microphone_active] = useState(false);
    const [microphone_setup_complete, set_microphone_setup_complete] = useState(false);
    const [microphone_requesting, set_microphone_requesting] = useState(false);
    const [audio_level, set_audio_level] = useState(0);
    const [latest_assistant, set_latest_assistant] = useState('');
    const [loaded, set_loaded] = useState(false);
    const websocket_ref = useRef<WebSocket | null>(null);
    const recorder_ref = useRef<MediaRecorder | null>(null);
    const stream_ref = useRef<MediaStream | null>(null);
    const last_audio_ref = useRef<HTMLAudioElement | null>(null);
    const speech_speed_ref = useRef(1);
    const voice_enabled_ref = useRef(true);
    const audio_playing_ref = useRef(false);
    const audio_context_ref = useRef<AudioContext | null>(null);
    const analyser_ref = useRef<AnalyserNode | null>(null);
    const level_buffer_ref = useRef<Uint8Array | null>(null);
    const silence_frame_ref = useRef<number | null>(null);
    const speech_started_ref = useRef(false);
    const last_speech_ref = useRef(0);
    const last_level_update_ref = useRef(0);
    const microphone_mode_ref = useRef<MicrophoneMode>('open');
    const pending_transcript_ref = useRef('');
    const discard_recording_ref = useRef(false);
    const pending_audio_ref = useRef<ArrayBuffer[]>([]);

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
        pending_transcript_ref.current = pending_transcript;
    }, [pending_transcript]);

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
        } catch (caught) {
            set_error(caught instanceof Error ? caught.message : t('errors.request'));
            set_microphone_setup_complete(true);
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
            set_microphone_setup_complete(true);
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
        const audio_blocked_message = t('errors.audioBlocked');
        audio.playbackRate = speech_speed_ref.current;
        audio.onplaying = () => {
            if (last_audio_ref.current !== audio) {
                return;
            }

            set_error((current) => current === audio_blocked_message ? '' : current);
        };
        audio.onended = () => {
            if (last_audio_ref.current !== audio) {
                return;
            }

            audio_playing_ref.current = false;
            set_status('ready');
        };
        last_audio_ref.current = audio;

        if (!voice_enabled_ref.current) {
            return;
        }

        audio_playing_ref.current = true;
        set_status('speaking');
        audio.play().catch((play_error) => {
            if (last_audio_ref.current !== audio) {
                return;
            }

            audio_playing_ref.current = false;
            set_status('ready');

            if (play_error instanceof DOMException && play_error.name === 'NotAllowedError') {
                set_error(audio_blocked_message);
            }
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
            pending_transcript_ref.current = message.text;
            set_pending_transcript(message.text);
        } else if (message.type === 'ended') {
            release_microphone(true);
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
        if (websocket_ref.current && (websocket_ref.current.readyState === WebSocket.CONNECTING || websocket_ref.current.readyState === WebSocket.OPEN)) {
            return;
        }

        set_status('connecting');
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const socket = new WebSocket(`${protocol}://${window.location.host}/ws/interviews/${interview_id}/`);
        socket.binaryType = 'arraybuffer';
        socket.onopen = () => {
            pending_audio_ref.current.forEach((buffer) => socket.send(buffer));
            pending_audio_ref.current = [];
        };
        socket.onmessage = handle_socket_message;
        socket.onerror = () => set_error(t('errors.connection'));
        socket.onclose = (event) => {
            if (event.code === 4429) {
                set_error(t('errors.workerBusy'));
                set_status('idle');
                release_microphone(true);
            } else if ([4401, 4404, 4500].includes(event.code) && !ended) {
                set_status('idle');
                release_microphone(true);
            }
        };
        websocket_ref.current = socket;
    }

    function send_text(text: string) {
        const value = text.trim();

        if (!value || !websocket_ref.current || websocket_ref.current.readyState !== WebSocket.OPEN) {
            return false;
        }

        pending_transcript_ref.current = '';
        set_pending_transcript('');
        websocket_ref.current.send(JSON.stringify({type: 'text', text: value}));
        set_status('thinking');
        return true;
    }

    function create_microphone_monitor(stream: MediaStream) {
        stop_microphone_monitor();
        const audio_context = new AudioContext();
        audio_context.resume().catch(() => undefined);
        const source = audio_context.createMediaStreamSource(stream);
        const analyser = audio_context.createAnalyser();
        analyser.fftSize = 2048;
        analyser.smoothingTimeConstant = 0.2;
        source.connect(analyser);
        audio_context_ref.current = audio_context;
        analyser_ref.current = analyser;
        level_buffer_ref.current = new Uint8Array(analyser.fftSize);
        silence_frame_ref.current = window.requestAnimationFrame(monitor_microphone);
    }

    function monitor_microphone() {
        const analyser = analyser_ref.current;
        const level_buffer = level_buffer_ref.current;
        const stream = stream_ref.current;

        if (!analyser || !level_buffer || !stream?.active) {
            return;
        }

        analyser.getByteTimeDomainData(level_buffer);
        let energy = 0;

        for (const sample of level_buffer) {
            const level = (sample - 128) / 128;
            energy += level * level;
        }

        const rms = Math.sqrt(energy / level_buffer.length);
        const now = performance.now();

        if (now - last_level_update_ref.current >= 80) {
            set_audio_level(Math.min(1, rms / 0.12));
            last_level_update_ref.current = now;
        }

        if (microphone_mode_ref.current === 'open' && !pending_transcript_ref.current) {
            if (rms >= SPEECH_THRESHOLD) {
                last_speech_ref.current = now;

                if (!speech_started_ref.current && !recorder_ref.current) {
                    speech_started_ref.current = true;
                    start_media_recorder(stream, false);
                }
            } else if (speech_started_ref.current && now - last_speech_ref.current >= SILENCE_MS) {
                speech_started_ref.current = false;
                last_speech_ref.current = 0;
                stop_recording();
            }
        } else {
            speech_started_ref.current = false;
            last_speech_ref.current = 0;
        }

        silence_frame_ref.current = window.requestAnimationFrame(monitor_microphone);
    }

    function stop_microphone_monitor() {
        if (silence_frame_ref.current !== null) {
            window.cancelAnimationFrame(silence_frame_ref.current);
            silence_frame_ref.current = null;
        }

        analyser_ref.current = null;
        level_buffer_ref.current = null;
        speech_started_ref.current = false;
        last_speech_ref.current = 0;
        last_level_update_ref.current = 0;
        set_audio_level(0);

        if (audio_context_ref.current) {
            audio_context_ref.current.close().catch(() => undefined);
            audio_context_ref.current = null;
        }
    }

    function start_media_recorder(stream: MediaStream, manual: boolean) {
        if (recorder_ref.current) {
            return;
        }

        const supported_types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
        const mime_type = supported_types.find((item) => MediaRecorder.isTypeSupported(item)) || '';
        const recorder = mime_type ? new MediaRecorder(stream, {mimeType: mime_type}) : new MediaRecorder(stream);
        const chunks: Blob[] = [];
        discard_recording_ref.current = false;
        recorder_ref.current = recorder;
        recorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                chunks.push(event.data);
            }
        };
        recorder.onstop = async () => {
            const discard = discard_recording_ref.current;
            discard_recording_ref.current = false;
            recorder_ref.current = null;
            set_is_recording(false);

            if (!discard && chunks.length > 0) {
                const blob = new Blob(chunks, {type: recorder.mimeType || mime_type});
                const buffer = await blob.arrayBuffer();

                if (websocket_ref.current?.readyState === WebSocket.OPEN) {
                    websocket_ref.current.send(buffer);
                } else {
                    pending_audio_ref.current.push(buffer);
                }

                set_status('transcribing');
            }

            if (microphone_mode_ref.current === 'closed') {
                stop_microphone_monitor();
                stream.getTracks().forEach((track) => track.stop());

                if (stream_ref.current === stream) {
                    stream_ref.current = null;
                }

                set_microphone_active(false);
            }
        };
        recorder.start();
        set_is_recording(true);

        if (manual) {
            set_status('listening');
        }
    }

    function enable_open_microphone() {
        set_error('');
        microphone_mode_ref.current = 'open';
        set_microphone_mode('open');

        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
            set_error(t('errors.microphone'));
            return;
        }

        if (stream_ref.current?.active) {
            set_microphone_active(true);
            set_microphone_setup_complete(true);
            connect_session();
            return;
        }

        set_microphone_requesting(true);
        navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}}).then((stream) => {
            stream_ref.current = stream;
            create_microphone_monitor(stream);
            set_microphone_active(true);
            set_microphone_setup_complete(true);
            set_microphone_requesting(false);
            connect_session();
        }).catch(() => {
            set_microphone_requesting(false);
            set_error(t('errors.microphoneDenied'));
        });
    }

    function use_closed_microphone() {
        set_error('');
        microphone_mode_ref.current = 'closed';
        set_microphone_mode('closed');
        release_microphone(true);
        set_microphone_setup_complete(true);
        connect_session();
    }

    function close_open_microphone() {
        microphone_mode_ref.current = 'closed';
        set_microphone_mode('closed');

        if (recorder_ref.current?.state === 'recording') {
            stop_recording();
            return;
        }

        release_microphone(true);
    }

    function start_recording() {
        set_error('');

        if (microphone_mode_ref.current === 'open') {
            return;
        }

        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
            set_error(t('errors.microphone'));
            return;
        }

        set_microphone_requesting(true);
        navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}}).then((stream) => {
            stream_ref.current = stream;
            create_microphone_monitor(stream);
            set_microphone_active(true);
            set_microphone_requesting(false);
            start_media_recorder(stream, true);
        }).catch(() => {
            set_microphone_requesting(false);
            set_error(t('errors.microphoneDenied'));
        });
    }

    function stop_recording() {
        if (recorder_ref.current?.state === 'recording') {
            recorder_ref.current.stop();
        }

        set_is_recording(false);
    }

    function release_microphone(discard_recording: boolean) {
        stop_microphone_monitor();

        if (recorder_ref.current?.state === 'recording') {
            discard_recording_ref.current = discard_recording;
            recorder_ref.current.stop();
        }

        stream_ref.current?.getTracks().forEach((track) => track.stop());
        stream_ref.current = null;
        set_microphone_active(false);
        set_is_recording(false);
    }

    function confirm_transcript(text: string) {
        websocket_ref.current?.send(JSON.stringify({type: 'confirm_transcript', text}));
        pending_transcript_ref.current = '';
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
            if (last_audio_ref.current) {
                audio_playing_ref.current = false;
                set_status('ready');
            }
        });
    }

    function cleanup_resources() {
        release_microphone(true);

        if (last_audio_ref.current) {
            last_audio_ref.current.pause();
            URL.revokeObjectURL(last_audio_ref.current.src);
            last_audio_ref.current = null;
        }

        audio_playing_ref.current = false;
        pending_audio_ref.current = [];
        websocket_ref.current?.close();
        websocket_ref.current = null;
    }

    return {
        interview_id, job, application_id, messages, status, error, pending_transcript, ended, result, review_requested, speech_speed,
        set_speech_speed, voice_enabled, set_voice_enabled, is_recording, microphone_mode, microphone_active, microphone_setup_complete,
        microphone_requesting, audio_level, latest_assistant, loaded, send_text, enable_open_microphone, use_closed_microphone,
        close_open_microphone, start_recording, stop_recording, confirm_transcript, rephrase, need_moment, end_interview, replay, refresh_status,
    };
}

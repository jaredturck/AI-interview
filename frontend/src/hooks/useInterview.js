import { useEffect, useRef, useState } from 'react';

import { get_interview_status, start_interview } from '../api';

export default function useInterview() {
    const [session, set_session] = useState(null);
    const [messages, set_messages] = useState([]);
    const [status, set_status] = useState('idle');
    const [error, set_error] = useState('');
    const [pending_transcript, set_pending_transcript] = useState('');
    const [ended, set_ended] = useState(false);
    const [result, set_result] = useState('');
    const [review_requested, set_review_requested] = useState(false);
    const [speech_speed, set_speech_speed] = useState(1);
    const [voice_enabled, set_voice_enabled] = useState(true);
    const [is_recording, set_is_recording] = useState(false);
    const [latest_assistant, set_latest_assistant] = useState('');
    const websocket_ref = useRef(null);
    const recorder_ref = useRef(null);
    const stream_ref = useRef(null);
    const last_audio_ref = useRef(null);
    const speech_speed_ref = useRef(1);
    const voice_enabled_ref = useRef(true);
    const audio_playing_ref = useRef(false);

    useEffect(() => {
        speech_speed_ref.current = speech_speed;

        if (last_audio_ref.current) {
            last_audio_ref.current.playbackRate = speech_speed;
        }
    }, [speech_speed]);

    useEffect(() => {
        voice_enabled_ref.current = voice_enabled;

        if (!voice_enabled && last_audio_ref.current) {
            last_audio_ref.current.pause();
            audio_playing_ref.current = false;
            set_status('ready');
        }
    }, [voice_enabled]);

    useEffect(() => {
        if (!ended || !session) {
            return undefined;
        }

        const poll = window.setInterval(() => {
            get_interview_status(session.interview_id).then((data) => {
                set_review_requested(Boolean(data.review_requested));

                if (data.result) {
                    set_result(data.result);
                    set_status('complete');
                    window.clearInterval(poll);
                } else if (data.status === 'evaluation_failed') {
                    set_status('evaluation_failed');
                    window.clearInterval(poll);
                }
            }).catch(() => {});
        }, 3000);

        return () => window.clearInterval(poll);
    }, [ended, session]);

    function append_message(role, text) {
        set_messages((current) => [...current, {role, text, id: crypto.randomUUID()}]);

        if (role === 'assistant') {
            set_latest_assistant(text);
        }
    }

    function play_audio(buffer) {
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
            set_error('Audio playback was blocked by the browser. The interviewer question is still available as text.');
        });
    }

    function handle_socket_message(event) {
        if (event.data instanceof ArrayBuffer) {
            play_audio(event.data);
            return;
        }

        const message = JSON.parse(event.data);

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
            set_status(message.status === 'evaluation_failed' ? 'evaluation_failed' : 'complete');
            set_result(message.result || '');
        } else if (message.type === 'audio_unavailable') {
            set_error('Interviewer audio is temporarily unavailable. The question is still available as text.');
        } else if (message.type === 'error') {
            set_error(message.message);
            set_status('ready');
        }
    }

    function connect_session(data) {
        set_session(data);
        set_status('connecting');
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const socket = new WebSocket(`${protocol}://${window.location.host}/ws/interviews/${data.interview_id}/`);
        socket.binaryType = 'arraybuffer';
        socket.onmessage = handle_socket_message;
        socket.onerror = () => set_error('The interview connection was interrupted. You can return to your account and resume the interview.');
        socket.onclose = (event) => {
            if ([4401, 4404].includes(event.code)) {
                sessionStorage.removeItem('ai_interview_id');
                set_session(null);
                set_status('idle');
            } else if (event.code === 4429) {
                set_error('The interview worker is currently busy. Please try again shortly.');
                set_session(null);
                set_status('idle');
            }
        };
        websocket_ref.current = socket;
    }

    async function begin(payload) {
        set_error('');
        const data = await start_interview(payload);
        sessionStorage.setItem('ai_interview_id', data.interview_id);
        set_messages([]);
        set_ended(false);
        set_result('');
        set_review_requested(false);
        connect_session(data);
        return data;
    }

    async function resume(interview_id, job_title) {
        const current = await get_interview_status(interview_id);
        const data = {interview_id, job_title};
        set_session(data);
        set_result(current.result || '');
        set_review_requested(Boolean(current.review_requested));

        if (['completed', 'terminated', 'evaluating', 'evaluated', 'evaluation_failed'].includes(current.status)) {
            set_ended(true);
            set_status(current.status === 'evaluation_failed' ? 'evaluation_failed' : 'complete');
            return;
        }

        sessionStorage.setItem('ai_interview_id', interview_id);
        connect_session(data);
    }

    function send_text(text) {
        const value = text.trim();

        if (!value || !websocket_ref.current || websocket_ref.current.readyState !== WebSocket.OPEN) {
            return;
        }

        set_pending_transcript('');
        websocket_ref.current.send(JSON.stringify({type: 'text', text: value}));
    }

    function start_recording() {
        set_error('');

        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
            set_error('Microphone recording is unavailable in this browser. You can continue by typing.');
            return;
        }

        navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
        }).then((stream) => {
            stream_ref.current = stream;
            const supported_types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
            const mime_type = supported_types.find((item) => MediaRecorder.isTypeSupported(item)) || '';
            const recorder = mime_type ? new MediaRecorder(stream, {mimeType: mime_type}) : new MediaRecorder(stream);
            const chunks = [];
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
        }).catch(() => set_error('The microphone is unavailable. You can continue by typing.'));
    }

    function stop_recording() {
        if (recorder_ref.current?.state === 'recording') {
            recorder_ref.current.stop();
        }

        set_is_recording(false);
    }

    function confirm_transcript(text) {
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

    function reset() {
        if (recorder_ref.current?.state === 'recording') {
            recorder_ref.current.stop();
        }

        stream_ref.current?.getTracks().forEach((track) => track.stop());
        stream_ref.current = null;
        recorder_ref.current = null;
        set_is_recording(false);

        if (last_audio_ref.current) {
            last_audio_ref.current.pause();
            URL.revokeObjectURL(last_audio_ref.current.src);
            last_audio_ref.current = null;
        }

        audio_playing_ref.current = false;
        websocket_ref.current?.close();
        websocket_ref.current = null;
        sessionStorage.removeItem('ai_interview_id');
        set_session(null);
        set_messages([]);
        set_status('idle');
        set_error('');
        set_pending_transcript('');
        set_ended(false);
        set_result('');
        set_review_requested(false);
    }

    return {
        session, messages, status, error, pending_transcript, ended, result, review_requested, speech_speed, set_speech_speed,
        voice_enabled, set_voice_enabled, is_recording, latest_assistant, begin, resume, send_text,
        start_recording, stop_recording, confirm_transcript, rephrase, need_moment, end_interview, replay, reset,
    };
}

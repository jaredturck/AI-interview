import InterviewControls from './InterviewControls';
import Transcript from './Transcript';
import TranscriptConfirmation from './TranscriptConfirmation';

const STATUS_LABELS = {
    connecting: 'Connecting',
    loading: 'Loading interviewer',
    ready: 'Ready for your answer',
    listening: 'Listening',
    transcribing: 'Transcribing',
    confirming: 'Waiting for transcript confirmation',
    thinking: 'Thinking',
    speaking: 'Speaking',
    paused: 'Take your time',
    complete: 'Interview complete',
};

export default function InterviewScreen({interview, on_account}) {
    return (
        <main className='flex min-h-screen flex-col bg-slate-950 text-white'>
            <div className='sr-only' aria-live='polite' aria-atomic='true'>{interview.latest_assistant}</div>
            <header className='border-b border-white/10 bg-slate-950/95 px-4 py-3 sm:px-6'>
                <div className='mx-auto flex max-w-6xl items-center justify-between gap-4'>
                    <div className='flex items-center gap-3'>
                        <div aria-hidden='true' className='grid h-11 w-11 place-items-center rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 font-bold text-white'>AI</div>
                        <div>
                            <div className='font-semibold'>Technical interviewer</div>
                            <div className='text-sm text-slate-400'>{interview.session?.job_title}</div>
                        </div>
                    </div>
                    <div className='flex items-center gap-2'>
                        <div role='status' className='rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200'>
                            {STATUS_LABELS[interview.status] || interview.status}
                        </div>
                        <button type='button' onClick={on_account} className='min-h-11 rounded-xl border border-slate-700 px-3 text-sm text-slate-200 hover:bg-white/5'>Account</button>
                    </div>
                </div>
            </header>

            {interview.error && <div role='alert' className='border-b border-red-400/30 bg-red-500/10 px-4 py-3 text-center text-sm text-red-100'>{interview.error}</div>}
            <Transcript messages={interview.messages} />
            <TranscriptConfirmation text={interview.pending_transcript} on_confirm={interview.confirm_transcript} />
            <InterviewControls interview={interview} />
        </main>
    );
}

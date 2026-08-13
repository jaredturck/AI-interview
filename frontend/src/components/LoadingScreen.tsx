import { useTranslation } from 'react-i18next';

export default function LoadingScreen({message}: {message?: string}) {
    const {t} = useTranslation();
    return (
        <main className="grid min-h-screen place-items-center px-6 text-slate-300">
            <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-slate-950/60 px-5 py-4 shadow-xl">
                <span className="loading-dot" aria-hidden="true" />
                <span>{message || t('common.loading')}</span>
            </div>
        </main>
    );
}

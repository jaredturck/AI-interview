import { useTranslation } from 'react-i18next';

const LANGUAGES = [
    ['en', 'English'], ['fr', 'Français'], ['de', 'Deutsch'], ['es', 'Español'],
    ['it', 'Italiano'], ['pt', 'Português'], ['nl', 'Nederlands'], ['pl', 'Polski']
];

export default function LanguageSelector({compact = false}: {compact?: boolean}) {
    const {i18n, t} = useTranslation();
    const language = (i18n.resolvedLanguage || i18n.language || 'en').split('-')[0];

    return (
        <label className={`language-selector ${compact ? 'language-selector-compact' : ''}`}>
            <span className="sr-only">{t('common.language')}</span>
            <select aria-label={t('common.language')} value={language} onChange={(event) => i18n.changeLanguage(event.target.value)}>
                {LANGUAGES.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
            </select>
        </label>
    );
}

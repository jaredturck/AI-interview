import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import LanguageSelector from './LanguageSelector';
import { useAuth } from '../hooks/useAuth';

export default function AppShell() {
    const {t} = useTranslation();
    const {auth, sign_out} = useAuth();
    const navigate = useNavigate();

    async function logout() {
        await sign_out();
        navigate('/login', {replace: true});
    }

    return (
        <div className="min-h-screen text-white">
            <header className="site-header">
                <div className="site-header-inner">
                    <NavLink to="/jobs" className="site-brand">
                        <span className="brand-mark">AI</span>
                        <span>{t('auth.brand')}</span>
                    </NavLink>
                    <nav className="site-nav" aria-label={`${t('common.jobs')} / ${t('common.account')}`}>
                        <NavLink to="/jobs" className={({isActive}) => isActive ? 'active' : ''}>{t('common.jobs')}</NavLink>
                        <NavLink to="/account" className={({isActive}) => isActive ? 'active' : ''}>{t('common.account')}</NavLink>
                    </nav>
                    <div className="site-header-actions">
                        <LanguageSelector compact />
                        <span className="header-email">{auth?.email}</span>
                        <button type="button" onClick={logout} className="ghost-button">{t('common.signOut')}</button>
                    </div>
                </div>
            </header>
            <Outlet />
        </div>
    );
}

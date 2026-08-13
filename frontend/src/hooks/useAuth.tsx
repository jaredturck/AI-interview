import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

import { get_auth_status, login as api_login, logout as api_logout, signup as api_signup } from '../api';
import type { AuthStatus } from '../types';

interface AuthContextValue {
    auth: AuthStatus | null;
    loading: boolean;
    error: string;
    sign_in: (email: string, password: string) => Promise<void>;
    sign_up: (email: string, password: string) => Promise<void>;
    sign_out: () => Promise<void>;
    refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({children}: {children: ReactNode}) {
    const [auth, set_auth] = useState<AuthStatus | null>(null);
    const [loading, set_loading] = useState(true);
    const [error, set_error] = useState('');

    useEffect(() => {
        refresh().finally(() => set_loading(false));
    }, []);

    async function refresh() {
        set_error('');

        try {
            set_auth(await get_auth_status());
        } catch (caught) {
            set_error(caught instanceof Error ? caught.message : '');
            set_auth({authenticated: false});
        }
    }

    async function sign_in(email: string, password: string) {
        set_error('');
        set_auth(await api_login(email, password));
    }

    async function sign_up(email: string, password: string) {
        set_error('');
        set_auth(await api_signup(email, password));
    }

    async function sign_out() {
        set_error('');
        set_auth(await api_logout());
    }

    return <AuthContext.Provider value={{auth, loading, error, sign_in, sign_up, sign_out, refresh}}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const context = useContext(AuthContext);

    if (!context) {
        throw new Error('useAuth must be used inside AuthProvider.');
    }

    return context;
}

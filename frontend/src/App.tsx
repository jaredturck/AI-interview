import { Navigate, Outlet, Route, Routes } from 'react-router-dom';

import AppShell from './components/AppShell';
import LoadingScreen from './components/LoadingScreen';
import { useAuth } from './hooks/useAuth';
import AccountPage from './pages/AccountPage';
import ApplicationPage from './pages/ApplicationPage';
import AuthPage from './pages/AuthPage';
import InterviewPage from './pages/InterviewPage';
import InterviewSetupPage from './pages/InterviewSetupPage';
import JobDetailPage from './pages/JobDetailPage';
import JobsPage from './pages/JobsPage';

function RequireAuth() {
    const {auth, loading} = useAuth();

    if (loading) {
        return <LoadingScreen />;
    }

    return auth?.authenticated ? <Outlet /> : <Navigate to="/login" replace />;
}

function GuestOnly() {
    const {auth, loading} = useAuth();

    if (loading) {
        return <LoadingScreen />;
    }

    return auth?.authenticated ? <Navigate to="/jobs" replace /> : <Outlet />;
}

function HomeRedirect() {
    const {auth, loading} = useAuth();

    if (loading) {
        return <LoadingScreen />;
    }

    return <Navigate to={auth?.authenticated ? '/jobs' : '/login'} replace />;
}

export default function App() {
    return (
        <Routes>
            <Route element={<GuestOnly />}>
                <Route path="/login" element={<AuthPage mode="login" />} />
                <Route path="/signup" element={<AuthPage mode="signup" />} />
            </Route>
            <Route element={<RequireAuth />}>
                <Route element={<AppShell />}>
                    <Route path="/jobs" element={<JobsPage />} />
                    <Route path="/jobs/:job_id" element={<JobDetailPage />} />
                    <Route path="/account" element={<AccountPage />} />
                    <Route path="/applications/:application_id" element={<ApplicationPage />} />
                    <Route path="/applications/:application_id/interview" element={<InterviewSetupPage />} />
                </Route>
                <Route path="/interviews/:interview_id" element={<InterviewPage />} />
            </Route>
            <Route path="/" element={<HomeRedirect />} />
            <Route path="*" element={<HomeRedirect />} />
        </Routes>
    );
}

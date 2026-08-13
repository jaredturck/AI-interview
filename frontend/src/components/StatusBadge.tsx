import { useTranslation } from 'react-i18next';

import type { ApplicationStatus, InterviewResult, InterviewStatus, LiveStatus } from '../types';

interface StatusBadgeProps {
    application_status?: ApplicationStatus;
    interview_status?: InterviewStatus;
    live_status?: LiveStatus;
    result?: InterviewResult;
}

export default function StatusBadge({application_status, interview_status, live_status, result}: StatusBadgeProps) {
    const {t} = useTranslation();
    let text = t('common.pending');
    let status = 'pending';

    if (result) {
        text = t(`result.${result}`);
        status = result.toLowerCase();
    } else if (live_status) {
        text = t(`liveStatus.${live_status}`);
        status = live_status;
    } else if (interview_status) {
        text = t(`interviewStatus.${interview_status}`);
        status = interview_status;
    } else if (application_status) {
        text = t(`applicationStatus.${application_status}`);
        status = application_status;
    }

    return <span className={`status-pill status-${status}`}>{text}</span>;
}

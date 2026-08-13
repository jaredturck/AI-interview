''' Interview application configuration. '''

import logging, os, sys

from django.apps import AppConfig

LOGGER = logging.getLogger(__name__)

class InterviewsConfig(AppConfig):
    ''' Configure the interview Django application. '''
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'interviews'

    def ready(self):
        ''' Preload realtime interview models when the Django server starts. '''
        runserver = 'runserver' in sys.argv
        server_process = os.environ.get('RUN_MAIN') == 'true' or '--noreload' in sys.argv

        if not runserver or not server_process:
            return

        from interviews.services.runtime import model_runtime  # noqa: PLC0415

        LOGGER.warning('Loading realtime interview models onto the GPUs...')
        model_runtime.preload_live()
        LOGGER.warning('Realtime interview models are loaded and ready.')

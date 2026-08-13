''' Configure Django startup behavior for the interviews application. '''

import logging, os, sys

from django.apps import AppConfig

LOGGER = logging.getLogger(__name__)

class InterviewsConfig(AppConfig):
    ''' Register the interviews app and its realtime Qwen preload hook with Django. '''
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'interviews'

    def ready(self):
        ''' Preload the realtime Qwen stack in the runserver child so interviews start without model-loading delay. '''
        runserver = 'runserver' in sys.argv
        server_process = os.environ.get('RUN_MAIN') == 'true' or '--noreload' in sys.argv

        if not runserver or not server_process:
            return

        from interviews.services.runtime import model_runtime  # noqa: PLC0415

        LOGGER.warning('Loading realtime interview models onto the GPUs...')
        model_runtime.preload_live()
        LOGGER.warning('Realtime interview models are loaded and ready.')

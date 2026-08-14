''' Configure Django startup behavior for the interviews application. '''

import logging, os, sys

from django.apps import AppConfig

LOGGER = logging.getLogger(__name__)

class InterviewsConfig(AppConfig):
    ''' Register the interviews app and its permanently resident model preload hook with Django. '''
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'interviews'

    def ready(self):
        ''' Preload the complete model stack in the runserver child so interviews and evaluation avoid cold model swaps. '''
        runserver = 'runserver' in sys.argv
        server_process = os.environ.get('RUN_MAIN') == 'true' or '--noreload' in sys.argv

        if not runserver or not server_process:
            return

        from interviews.services.runtime import model_runtime  # noqa: PLC0415

        LOGGER.warning('Loading the resident interview and evaluation model stack onto the GPUs...')
        model_runtime.preload_models()
        LOGGER.warning('Resident interview and evaluation models are loaded and ready.')

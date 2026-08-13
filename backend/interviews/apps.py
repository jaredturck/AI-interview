''' Interview application configuration. '''

from django.apps import AppConfig

class InterviewsConfig(AppConfig):
    ''' Configure the interview Django application. '''
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'interviews'

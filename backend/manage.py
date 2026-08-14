#!/usr/bin/env python
''' Run Django management commands against the AI interview backend. '''

import os

from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_interviewer.settings')

def main():
    ''' Execute the requested Django management command in the parent process only. '''
    execute_from_command_line()

if __name__ == '__main__':
    main()

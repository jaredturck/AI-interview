#!/usr/bin/env python
''' Run Django management commands against the AI interview backend. '''

import os

from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_interviewer.settings')
execute_from_command_line()

from django.core.management.base import BaseCommand

from interviews.models import InterviewSession


class Command(BaseCommand):
    help = "Recover interview states that cannot survive a backend process restart."

    def handle(self, *args, **options):
        failed = InterviewSession.objects.filter(status="evaluating", result="").update(status="evaluation_failed")
        if failed:
            self.stdout.write(self.style.WARNING(f"Marked {failed} interrupted evaluation(s) as failed."))

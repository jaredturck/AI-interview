from django.core.management.base import BaseCommand

from interviews.services.evaluation import evaluate_interview


class Command(BaseCommand):
    help = "Run the final evaluator for one completed interview."

    def add_arguments(self, parser):
        parser.add_argument("interview_id")

    def handle(self, *args, **options):
        completed = evaluate_interview(options["interview_id"])
        if completed:
            self.stdout.write(self.style.SUCCESS("Evaluation completed."))
        else:
            self.stdout.write(self.style.WARNING("The evaluator could not reserve the model runtime."))

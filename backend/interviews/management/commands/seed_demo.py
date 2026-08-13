from pathlib import Path

from django.core.management.base import BaseCommand

from interviews.models import CompanyDocument, Job

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ROOT = PROJECT_ROOT / "config"


class Command(BaseCommand):
    help = "Load the demo job, evaluation questions and company documents."

    def handle(self, *args, **options):
        description = (CONFIG_ROOT / "job_description.md").read_text(encoding="utf-8").strip()
        questions = [
            line.strip()
            for line in (CONFIG_ROOT / "evaluation_questions.txt").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        Job.objects.update(is_active=False)
        job, _ = Job.objects.update_or_create(
            title="Software Developer — Backend Focus",
            defaults={
                "description": description,
                "evaluation_questions": questions,
                "is_active": True,
            },
        )

        CompanyDocument.objects.all().delete()
        for path in sorted((CONFIG_ROOT / "company").glob("*.md")):
            CompanyDocument.objects.create(title=path.stem.replace("_", " ").title(), content=path.read_text(encoding="utf-8"))

        self.stdout.write(self.style.SUCCESS(f"Seeded {job.title} with {len(questions)} evaluation questions."))

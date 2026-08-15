# Sample jobs

`python backend/manage.py seed_sample_jobs` creates ten optional demonstration vacancies. They are source-controlled test fixtures, not production hiring recommendations. Normal Django Admin job creation writes directly to the database and does not read `config/job_description.md` or `config/evaluation_questions.txt`.

The samples deliberately cover different levels of specialist knowledge so the adaptive interviewer and evaluator can be tested against genuine role differences. Each sample separates:

- candidate-facing description;
- interview-assessable essential requirements;
- requirements that must be verified outside the interview;
- broader evidence criteria.

The job wording and evidence areas were reviewed against the following primary or official career/professional sources on 15 August 2026. The source material informs the role content; the sample vacancies remain fictional.

| Sample | Research basis |
| --- | --- |
| Backend Software Developer | UK National Careers Service software developer profile; Django database transaction documentation; PostgreSQL index and `EXPLAIN` documentation. |
| Front-End Web Developer | UK National Careers Service web developer profile; W3C WCAG 2.2 keyboard requirements; MDN semantic HTML/accessibility guidance. |
| Embedded Firmware Engineer | UK National Careers Service electronics engineer profile; FreeRTOS documentation on tasks, queues, semaphores and mutexes. |
| Registered Nurse | Nursing and Midwifery Council Code and Standards of proficiency for registered nurses; NHS England NEWS2 deterioration guidance; Resuscitation Council UK ABCDE guidance. |
| Commercial Cleaner | UK National Careers Service cleaner profile; HSE COSHH guidance for cleaning work. |
| Installation Electrician | UK National Careers Service electrician profile. |
| Customer Service Advisor | UK National Careers Service customer service assistant profile. |
| Management Accountant | UK National Careers Service management accountant profile; CIMA description of management accounting work. |
| Secondary School Science Teacher | UK National Careers Service secondary school teacher profile; Department for Education Teachers' Standards; GOV.UK QTS guidance. |
| Warehouse Operative | UK National Careers Service warehouse worker profile. |

## Reference links

- https://nationalcareers.service.gov.uk/job-profiles/software-developer
- https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- https://www.postgresql.org/docs/current/indexes.html
- https://www.postgresql.org/docs/current/sql-explain.html
- https://nationalcareers.service.gov.uk/job-profiles/web-developer
- https://www.w3.org/TR/WCAG22/
- https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Accessibility/HTML
- https://nationalcareers.service.gov.uk/job-profiles/electronics-engineer
- https://www.freertos.org/Documentation/02-Kernel/02-Kernel-features/02-Queues-mutexes-and-semaphores/04-Mutexes
- https://www.nmc.org.uk/standards/standards-for-nurses/standards-of-proficiency-for-registered-nurses/
- https://www.nmc.org.uk/standards/code/
- https://www.england.nhs.uk/publication/patient-safety-alert-safe-adoption-of-news2/
- https://www.resus.org.uk/library/abcde-approach
- https://nationalcareers.service.gov.uk/job-profiles/cleaner
- https://www.hse.gov.uk/cleaning/topics/coshh.htm
- https://nationalcareers.service.gov.uk/job-profiles/electrician
- https://nationalcareers.service.gov.uk/job-profiles/customer-service-assistant
- https://nationalcareers.service.gov.uk/job-profiles/management-accountant
- https://myfuture.cimaglobal.com/starting-a-career-in-management-accounting/
- https://nationalcareers.service.gov.uk/job-profiles/secondary-school-teacher
- https://www.gov.uk/government/publications/teachers-standards
- https://getintoteaching.education.gov.uk/train-to-be-a-teacher/what-is-qts
- https://nationalcareers.service.gov.uk/job-profiles/warehouse-worker

## Seed behaviour

```bash
python backend/manage.py seed_sample_jobs
```

Creates missing samples and skips existing ones. Re-running the command is safe and does not create duplicates.

```bash
python backend/manage.py seed_sample_jobs --reset
```

Restores canonical content only for sample jobs with no applications. A sample job that already has applications is an immutable recruitment snapshot and is deliberately skipped.

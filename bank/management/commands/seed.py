"""
Populate the database with test data for local development.

Wipes every bank / presets / compiler row first so the command is
idempotent: `python manage.py seed` always leaves the same data behind.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from bank.models import Bullet, Component, Coursework, Education, Link, Profile, Skill
from compiler.models import Resume
from presets.models import PresetBullet, PresetComponent, PresetCoursework, PresetSkill, ResumePreset

# (category, title, organization, location, start, end, tech_stack, [bullets])
COMPONENTS = [
    (
        Component.Category.EXPERIENCE, 'Software Engineering Intern', 'Acme Corp', 'Seattle, WA',
        date(2025, 6, 1), date(2025, 8, 31), '',
        [
            'Built a **REST API** in Django serving 2M requests/day, cutting p95 latency by 40%',
            'Migrated legacy cron jobs to **Celery**, eliminating 3 recurring on-call pages per week',
            'Wrote integration tests raising coverage from 55% to 85% on the billing service',
            'Led a two-week spike evaluating Postgres partitioning strategies for the events table',
        ],
    ),
    (
        Component.Category.EXPERIENCE, 'Undergraduate Research Assistant', 'State University CS Dept', 'Columbus, OH',
        date(2024, 9, 1), None, '',
        [
            'Implemented a **PyTorch** pipeline for training graph neural networks on citation datasets',
            'Reduced experiment turnaround from 6 hours to 45 minutes by batching GPU jobs with SLURM',
            'Co-authored a workshop paper accepted to a regional ML symposium',
        ],
    ),
    (
        Component.Category.EXPERIENCE, 'Teaching Assistant, Data Structures', 'State University', 'Columbus, OH',
        date(2024, 1, 8), date(2024, 5, 3), '',
        [
            'Held weekly office hours and graded assignments for a class of 120 students',
            'Wrote an autograder in Python that cut grading time for the course staff by half',
        ],
    ),
    (
        Component.Category.PROJECT, 'ResumeBank', '', '',
        date(2026, 8, 1), None, 'Django, SQLite, Jinja2, LaTeX',
        [
            'Designed a relational schema separating reusable resume components from per-resume presets',
            'Rendered **Jinja2** LaTeX templates and compiled them with pdflatex, tracking page counts with pypdf',
            'Built a preset-cloning workflow so tailoring a new resume starts from the previous one',
        ],
    ),
    (
        Component.Category.PROJECT, 'Trailhead', '', '',
        date(2025, 2, 1), date(2025, 5, 15), 'React, Node.js, PostgreSQL, Mapbox',
        [
            'Built a hiking-trail planner with **React** and Mapbox that overlays elevation profiles on routes',
            'Designed a PostGIS schema for 12k trails and exposed it through an Express API',
            'Deployed on Fly.io with GitHub Actions CI running lint, unit and end-to-end tests',
        ],
    ),
    (
        Component.Category.PROJECT, 'Tiny Shell', '', '',
        date(2024, 10, 1), date(2024, 11, 20), 'C, POSIX',
        [
            'Implemented a Unix shell in **C** supporting pipes, redirection, and job control',
            'Handled SIGCHLD and SIGINT correctly to reap background jobs without zombie processes',
        ],
    ),
    (
        Component.Category.LEADERSHIP, 'President', 'Association for Computing Machinery, Student Chapter', 'Columbus, OH',
        date(2025, 5, 1), None, '',
        [
            'Grew membership from 60 to 140 by launching a biweekly workshop series on practical tooling',
            'Organized a 24-hour hackathon with 200 participants and $5k in sponsorships',
        ],
    ),
    (
        Component.Category.LEADERSHIP, 'Mentor', 'CS Peer Mentoring Program', 'Columbus, OH',
        date(2024, 9, 1), date(2025, 5, 1), '',
        [
            'Mentored six first-year students through their first two programming courses',
        ],
    ),
    (
        Component.Category.HONOR, "Dean's List", 'State University', '',
        date(2025, 5, 1), None, '',
        [],
    ),
    (
        Component.Category.HONOR, 'Best Technical Project', 'HackOhio 2024', '',
        date(2024, 10, 20), None, '',
        [],
    ),
    (
        Component.Category.CERTIFICATION, 'AWS Certified Cloud Practitioner', 'Amazon Web Services', '',
        date(2025, 3, 15), None, '',
        [],
    ),
]

SKILLS = {
    Skill.Group.LANGUAGES: ['Python', 'JavaScript', 'TypeScript', 'C', 'SQL', 'Java'],
    Skill.Group.FRAMEWORKS: ['Django', 'React', 'Node.js', 'PyTorch', 'Express'],
    Skill.Group.TOOLS: ['Git', 'Docker', 'PostgreSQL', 'GitHub Actions', 'Linux', 'LaTeX'],
    Skill.Group.OTHER: ['Agile', 'Technical Writing'],
}


class Command(BaseCommand):
    help = 'Reset the database contents and load test data.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.clear()
        self.seed_profile()
        self.seed_education()
        components = self.seed_components()
        skills = self.seed_skills()
        self.seed_presets(components, skills)
        self.stdout.write(self.style.SUCCESS(
            f'Seeded {Component.objects.count()} components, {Bullet.objects.count()} bullets, '
            f'{Skill.objects.count()} skills, {ResumePreset.objects.count()} presets.'
        ))

    def clear(self):
        # Cascades take care of Link, Coursework, Bullet and the Preset* tables.
        Resume.objects.all().delete()
        ResumePreset.objects.all().delete()
        Component.objects.all().delete()
        Skill.objects.all().delete()
        Education.objects.all().delete()
        Profile.objects.all().delete()

    def seed_profile(self):
        profile = Profile.load()
        profile.name = 'Jane Doe'
        profile.email = 'jane.doe@example.com'
        profile.phone = '(555) 123-4567'
        profile.location = 'Columbus, OH'
        profile.save()
        Link.objects.bulk_create([
            Link(profile=profile, link_type=Link.LinkType.LINKEDIN, url='https://linkedin.com/in/janedoe', order=0),
            Link(profile=profile, link_type=Link.LinkType.GITHUB, url='https://github.com/janedoe', order=1),
            Link(profile=profile, link_type=Link.LinkType.PORTFOLIO, url='https://janedoe.dev', order=2),
        ])

    def seed_education(self):
        edu = Education.objects.create(
            school='State University',
            degree='B.S. Computer Science',
            location='Columbus, OH',
            start_date=date(2023, 8, 20),
            end_date=date(2027, 5, 10),
            gpa='3.85',
        )
        Coursework.objects.bulk_create([
            Coursework(education=edu, name=name, order=i)
            for i, name in enumerate([
                'Data Structures', 'Algorithms', 'Operating Systems', 'Databases',
                'Computer Networks', 'Machine Learning',
            ])
        ])

    def seed_components(self):
        """Returns components keyed by title so presets can reference them."""
        components = {}
        for category, title, org, location, start, end, tech, bullets in COMPONENTS:
            comp = Component.objects.create(
                category=category, title=title, organization=org, location=location,
                start_date=start, end_date=end, tech_stack=tech,
            )
            Bullet.objects.bulk_create([
                Bullet(component=comp, text=text, order=i) for i, text in enumerate(bullets)
            ])
            components[title] = comp
        return components

    def seed_skills(self):
        """Returns skills keyed by name."""
        skills = {}
        for group, names in SKILLS.items():
            for i, name in enumerate(names):
                skills[name] = Skill.objects.create(group=group, name=name, order=i)
        return skills

    def seed_presets(self, components, skills):
        # An "everything" preset, plus two tailored ones that trim bullets and
        # drop components to exercise selection + ordering.
        self.make_preset(
            'General',
            components=[
                # (title, bullet indices; None means every bullet)
                ('Software Engineering Intern', None),
                ('Undergraduate Research Assistant', None),
                ('Teaching Assistant, Data Structures', None),
                ('ResumeBank', None),
                ('Trailhead', None),
                ('Tiny Shell', None),
                ('President', None),
                ('Mentor', None),
                ("Dean's List", None),
                ('Best Technical Project', None),
                ('AWS Certified Cloud Practitioner', None),
            ],
            skill_names=list(skills),
            components_by_title=components, skills_by_name=skills,
        )
        self.make_preset(
            'Backend Internship',
            components=[
                ('Software Engineering Intern', [0, 1, 2]),
                ('Undergraduate Research Assistant', [1]),
                ('ResumeBank', [0, 1]),
                ('Tiny Shell', [0, 1]),
                ('President', [1]),
                ('AWS Certified Cloud Practitioner', None),
            ],
            skill_names=['Python', 'SQL', 'C', 'Django', 'PostgreSQL', 'Docker', 'Git', 'Linux'],
            components_by_title=components, skills_by_name=skills,
            course_names=['Databases', 'Operating Systems', 'Computer Networks'],
        )
        self.make_preset(
            'ML Research',
            components=[
                ('Undergraduate Research Assistant', None),
                ('Software Engineering Intern', [0, 3]),
                ('Trailhead', [1]),
                ("Dean's List", None),
            ],
            skill_names=['Python', 'PyTorch', 'SQL', 'Linux', 'Git', 'LaTeX', 'Technical Writing'],
            components_by_title=components, skills_by_name=skills,
            course_names=['Machine Learning', 'Algorithms'],
            page_limit=2,
        )

    def make_preset(self, name, components, skill_names, components_by_title, skills_by_name,
                    course_names=None, **fields):
        """course_names=None picks every course in bank order; a list picks those, in that order."""
        preset = ResumePreset.objects.create(name=name, **fields)
        for order, (title, bullet_indices) in enumerate(components):
            comp = components_by_title[title]
            pc = PresetComponent.objects.create(preset=preset, component=comp, order=order)
            bullets = list(comp.bullets.all())
            chosen = bullets if bullet_indices is None else [bullets[i] for i in bullet_indices]
            PresetBullet.objects.bulk_create([
                PresetBullet(preset_component=pc, bullet=b, order=i) for i, b in enumerate(chosen)
            ])
        PresetSkill.objects.bulk_create([
            PresetSkill(preset=preset, skill=skills_by_name[n], order=i) for i, n in enumerate(skill_names)
        ])
        courses = list(Coursework.objects.all())
        if course_names is not None:
            by_name = {c.name: c for c in courses}
            courses = [by_name[n] for n in course_names]
        PresetCoursework.objects.bulk_create([
            PresetCoursework(preset=preset, coursework=c, order=i) for i, c in enumerate(courses)
        ])
        return preset

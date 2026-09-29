"""
Source data that resumes are assembled from.

Every dated or bullet-bearing entry is a Component. Profile, Education and
Skill live in their own models because they render differently rather than
as bullet blocks. Presets (see presets.models) reference these rows by pk
through explicit join tables, so editing a row here propagates to every
preset that uses it.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from django.db import models

if TYPE_CHECKING:
    from presets.models import (
        PresetBullet, PresetComponent, PresetCoursework, PresetEducation, PresetLink, PresetSkill,
    )


class Profile(models.Model):
    """Resume header. Always exactly one row (pk=1); fetch it with Profile.load()."""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    location = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        profile, _ = cls.objects.get_or_create(pk=1)
        return profile

    def __str__(self):
        return self.name


class Link(models.Model):
    """A header link (LinkedIn, GitHub, ...). Only ever rendered under the Profile."""

    class LinkType(models.TextChoices):
        LINKEDIN = 'linkedin', 'LinkedIn'
        GITHUB = 'github', 'GitHub'
        PORTFOLIO = 'portfolio', 'Portfolio'
        OTHER = 'other', 'Other'

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='links')
    link_type = models.CharField(max_length=20, choices=LinkType.choices, default=LinkType.OTHER)
    url = models.URLField()
    order = models.PositiveIntegerField(default=0)

    # Added by Django at runtime; declared here for the type checker only.
    get_link_type_display: Callable[[], str]
    presetlink_set: models.Manager[PresetLink]

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.get_link_type_display()}: {self.url}'


class Education(models.Model):
    """
    A degree. GPA lives here rather than on Profile because it belongs to a specific degree.

    degree_title is optional; the PDF shows it abbreviated before the field of
    study (`display_degree`, e.g. "B.S. Computer Science").
    """

    class DegreeTitle(models.TextChoices):
        AA = 'AA', 'A.A.'
        AS = 'AS', 'A.S.'
        BA = 'BA', 'B.A.'
        BS = 'BS', 'B.S.'
        BENG = 'BEng', 'B.Eng.'
        MA = 'MA', 'M.A.'
        MS = 'MS', 'M.S.'
        MENG = 'MEng', 'M.Eng.'
        MBA = 'MBA', 'MBA'
        PHD = 'PhD', 'Ph.D.'

    school = models.CharField(max_length=200)
    degree_title = models.CharField(max_length=10, choices=DegreeTitle.choices, blank=True)
    degree = models.CharField('field of study', max_length=200)
    location = models.CharField(max_length=100, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    # Added by Django at runtime; declared here for the type checker only.
    get_degree_title_display: Callable[[], str]
    preseteducation_set: models.Manager[PresetEducation]

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.display_degree}, {self.school}'

    @property
    def display_degree(self):
        if not self.degree_title:
            return self.degree
        return f'{self.get_degree_title_display()} {self.degree}'


class Coursework(models.Model):
    education = models.ForeignKey(Education, on_delete=models.CASCADE, related_name='coursework')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    # Added by Django at runtime; declared here for the type checker only.
    presetcoursework_set: models.Manager[PresetCoursework]

    class Meta:
        ordering = ['order']
        verbose_name_plural = 'coursework'

    def __str__(self):
        return self.name


class Component(models.Model):
    """
    Single table for Experience, Project, Leadership, Honor and Certification.

    Date convention: Honor and Certification have a single date, stored in
    start_date (save() clears end_date). A Project shows start_date alone
    unless it has an end_date, then a range. For Experience and Leadership a
    null end_date means "Present". tech_stack is projects-only (save() clears
    it for other categories). in_progress is certifications-only (save()
    clears it otherwise): the PDF shows "In Progress" instead of the date,
    which is kept for when the cert is finished.
    """

    class Category(models.TextChoices):
        EXPERIENCE = 'experience', 'Experience'
        PROJECT = 'project', 'Project'
        LEADERSHIP = 'leadership', 'Leadership'
        HONOR = 'honor', 'Honor'
        CERTIFICATION = 'certification', 'Certification'

    category = models.CharField(max_length=20, choices=Category.choices)
    # Role, project name, honor name or cert name. Not unique: two internships
    # at different companies can share a title.
    title = models.CharField(max_length=200)
    # Company, org or issuer.
    organization = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    # Projects only; rendered as the "Name | Tech" line.
    tech_stack = models.CharField(max_length=200, blank=True)
    # Certifications only; rendered as "In Progress" in place of the date.
    in_progress = models.BooleanField(default=False)

    SINGLE_DATE = {Category.HONOR, Category.CERTIFICATION}

    # Added by Django at runtime; declared here for the type checker only.
    presetcomponent_set: models.Manager[PresetComponent]

    class Meta:
        ordering = ['category', '-start_date', 'title']

    def save(self, *args, **kwargs):
        if self.category in self.SINGLE_DATE:
            self.end_date = None
        if self.category != self.Category.PROJECT:
            self.tech_stack = ''
        if self.category != self.Category.CERTIFICATION:
            self.in_progress = False
        super().save(*args, **kwargs)

    def __str__(self):
        if self.organization:
            return f'{self.title} ({self.organization})'
        return self.title


class Bullet(models.Model):
    """
    A candidate bullet for a Component. Presets pick a subset in their own order.

    Plain text; `**bold**` is the only markup and is converted by the compiler.
    """

    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name='bullets')
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    # Added by Django at runtime; declared here for the type checker only.
    presetbullet_set: models.Manager[PresetBullet]

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text[:80]


class Skill(models.Model):
    """A single skill, grouped the way Jake's template renders the Skills section."""

    class Group(models.TextChoices):
        LANGUAGES = 'languages', 'Languages'
        FRAMEWORKS = 'frameworks', 'Frameworks'
        TOOLS = 'tools', 'Tools'
        OTHER = 'other', 'Other'

    group = models.CharField(max_length=20, choices=Group.choices, default=Group.OTHER)
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    # Added by Django at runtime; declared here for the type checker only.
    get_group_display: Callable[[], str]
    presetskill_set: models.Manager[PresetSkill]

    class Meta:
        ordering = ['group', 'order']

    def __str__(self):
        return self.name

"""
Source data that resumes are assembled from.

Every dated or bullet-bearing entry is a Component. Profile, Education and
Skill live in their own models because they render differently rather than
as bullet blocks. Presets (see presets.models) reference these rows by pk
through explicit join tables, so editing a row here propagates to every
preset that uses it.
"""
from django.db import models


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

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.get_link_type_display()}: {self.url}'


class Education(models.Model):
    """A degree. GPA lives here rather than on Profile because it belongs to a specific degree."""

    school = models.CharField(max_length=200)
    degree = models.CharField(max_length=200)
    location = models.CharField(max_length=100, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.degree}, {self.school}'


class Coursework(models.Model):
    education = models.ForeignKey(Education, on_delete=models.CASCADE, related_name='coursework')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name_plural = 'coursework'

    def __str__(self):
        return self.name


class Component(models.Model):
    """
    Single table for Experience, Project, Leadership, Honor and Certification.

    Date convention: Honor and Certification have a single date, stored in
    start_date. For the other categories a null end_date means "Present".
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

    class Meta:
        ordering = ['category', '-start_date', 'title']

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

    class Meta:
        ordering = ['group', 'order']

    def __str__(self):
        return self.name

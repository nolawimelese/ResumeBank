"""
A ResumePreset is a specific selection and ordering of bank rows.

A preset stores no lists of ids; what it includes is defined entirely by the
PresetComponent / PresetBullet / PresetSkill / PresetCoursework join tables.
Those hold references, not copies, so editing a Component, Bullet, Skill or
Coursework propagates to every preset that uses it. Delete-with-warning is a
query on the default reverse accessors: component.presetcomponent_set.exists(),
bullet.presetbullet_set.exists(), skill.presetskill_set.exists(),
coursework.presetcoursework_set.exists().
"""
from django.db import models


class ResumePreset(models.Model):
    class Template(models.TextChoices):
        JAKES = 'jakes', "Jake's Resume"

    name = models.CharField(max_length=100, unique=True)
    template = models.CharField(max_length=20, choices=Template.choices, default=Template.JAKES)
    # A toggle rather than a pick: GPA is a field on Education, not a row of its own.
    include_gpa = models.BooleanField(default=True)
    # Used for the over-limit check after compiling.
    page_limit = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PresetComponent(models.Model):
    """A Component included in a preset. Section order is fixed by the template;
    `order` only sorts Components within their own category section."""

    preset = models.ForeignKey(ResumePreset, on_delete=models.CASCADE, related_name='preset_components')
    component = models.ForeignKey('bank.Component', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(fields=['preset', 'component'], name='unique_component_per_preset'),
        ]

    def __str__(self):
        return f'{self.preset} / {self.component}'


class PresetBullet(models.Model):
    """A Bullet selected under a PresetComponent. Points at PresetComponent rather than
    the preset so a bullet can only be chosen under a Component that is itself in the preset."""

    preset_component = models.ForeignKey(PresetComponent, on_delete=models.CASCADE, related_name='preset_bullets')
    bullet = models.ForeignKey('bank.Bullet', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(fields=['preset_component', 'bullet'], name='unique_bullet_per_preset_component'),
        ]

    def __str__(self):
        return f'{self.preset_component} / {self.bullet}'


class PresetSkill(models.Model):
    preset = models.ForeignKey(ResumePreset, on_delete=models.CASCADE, related_name='preset_skills')
    skill = models.ForeignKey('bank.Skill', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(fields=['preset', 'skill'], name='unique_skill_per_preset'),
        ]

    def __str__(self):
        return f'{self.preset} / {self.skill}'


class PresetCoursework(models.Model):
    """A Coursework row included in a preset. Every Education always renders; this only
    picks which of its courses appear on the "Relevant Coursework" line, and in what order."""

    preset = models.ForeignKey(ResumePreset, on_delete=models.CASCADE, related_name='preset_coursework')
    coursework = models.ForeignKey('bank.Coursework', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name_plural = 'preset coursework'
        constraints = [
            models.UniqueConstraint(fields=['preset', 'coursework'], name='unique_coursework_per_preset'),
        ]

    def __str__(self):
        return f'{self.preset} / {self.coursework}'

from django.contrib import admin

from .models import (
    PresetBullet, PresetComponent, PresetCoursework, PresetEducation, PresetLink, PresetSkill, ResumePreset,
)


class PresetComponentInline(admin.TabularInline):
    model = PresetComponent
    extra = 1


class PresetLinkInline(admin.TabularInline):
    model = PresetLink
    extra = 1


class PresetSkillInline(admin.TabularInline):
    model = PresetSkill
    extra = 1


class PresetEducationInline(admin.TabularInline):
    model = PresetEducation
    extra = 1


class PresetCourseworkInline(admin.TabularInline):
    model = PresetCoursework
    extra = 1


@admin.register(ResumePreset)
class ResumePresetAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'page_limit', 'include_gpa', 'updated_at')
    inlines = [PresetLinkInline, PresetComponentInline, PresetSkillInline, PresetEducationInline, PresetCourseworkInline]


class PresetBulletInline(admin.TabularInline):
    model = PresetBullet
    extra = 1


# Registered standalone so bullets can be picked per PresetComponent
# (admin has no nested inlines).
@admin.register(PresetComponent)
class PresetComponentAdmin(admin.ModelAdmin):
    list_display = ('preset', 'component', 'order')
    list_filter = ('preset',)
    inlines = [PresetBulletInline]

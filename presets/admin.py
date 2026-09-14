from django.contrib import admin

from .models import PresetBullet, PresetComponent, PresetCoursework, PresetSkill, ResumePreset


class PresetComponentInline(admin.TabularInline):
    model = PresetComponent
    extra = 1


class PresetSkillInline(admin.TabularInline):
    model = PresetSkill
    extra = 1


class PresetCourseworkInline(admin.TabularInline):
    model = PresetCoursework
    extra = 1


@admin.register(ResumePreset)
class ResumePresetAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'page_limit', 'include_gpa', 'updated_at')
    inlines = [PresetComponentInline, PresetSkillInline, PresetCourseworkInline]


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
